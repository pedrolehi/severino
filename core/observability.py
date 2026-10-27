"""Langfuse: um trace por turno do grafo (nós, router, flows, RAG e LLM).

`langfuse_turn` abre o span raiz do turno com trace id derivado do `message_id`
do broker, pendura o CallbackHandler no `config` do `graph.invoke` e, no
`finish`, grava resposta, resumo, tags e notas. O feedback do usuário chega
depois por `score_feedback`, no mesmo trace. Sem chaves ou com
LANGFUSE_ENABLED=false, nada é enviado.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage
from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator

from core import config

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = frozenset(
    {
        "cpf",
        "pis",
        "pispasepnit",
        "email",
        "nome",
        "nome_social",
        "data_nascimento",
        "datanascimento",
        "dtnasc",
        "datanasc",
    }
)
_MASK = "***"
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# Metadados de trace são propagados como string de até 200 caracteres.
_TRACE_METADATA_KEYS = ("route", "flow", "fallback_reason", "judge_action", "collection_name")
_FEEDBACK_SCORE = "feedback_usuario"
_RAG_NO_RESULTS = "rag_retrieval:no_results"

_client: Langfuse | None = None
_seeded_trace_id: ContextVar[int | None] = ContextVar("_seeded_trace_id", default=None)


class SeededIdGenerator(RandomIdGenerator):
    """Trace id fixo para a raiz do turno.

    `trace_context` do SDK cria um pai fictício para a raiz; a tela de Sessions
    só monta a conversa a partir de observações sem pai.
    """

    def generate_trace_id(self) -> int:
        seeded = _seeded_trace_id.get()
        return seeded if seeded is not None else super().generate_trace_id()


def mask_text(text: str) -> str:
    return _EMAIL_RE.sub(_MASK, _CPF_RE.sub(_MASK, text))


def mask_sensitive(*, data: Any, **_: Any) -> Any:
    """Mascara PII por chave e CPF/e-mail dentro de textos (recursivo, sem mutar a origem)."""
    if isinstance(data, str):
        return mask_text(data)
    if isinstance(data, BaseMessage):
        return data.model_copy(update={"content": mask_sensitive(data=data.content)})
    if isinstance(data, dict):
        return {
            key: _MASK
            if isinstance(key, str) and key.lower() in _SENSITIVE_KEYS
            else mask_sensitive(data=value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive(data=item) for item in data]
    return data


def reset_langfuse_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.shutdown()
        except Exception:  # noqa: BLE001
            logger.debug("langfuse shutdown ignorado", exc_info=True)
    _client = None


def _get_client() -> Langfuse:
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
            environment=config.APP_ENV,
            mask=mask_sensitive,
            id_generator=SeededIdGenerator(),
        )
    return _client


class NodeRecorder(BaseCallbackHandler):
    """Anota os nós do LangGraph executados no turno.

    O estado vem do checkpointer, então `decision`, `rag_result` e
    `fallback_reason` podem ser de turnos anteriores; só valem se o nó rodou.
    """

    def __init__(self) -> None:
        super().__init__()
        self.nodes: set[str] = set()

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: Any,
        *,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        node = (metadata or {}).get("langgraph_node")
        if isinstance(node, str):
            self.nodes.add(node)


@dataclass
class LangfuseTurn:
    run_config: dict[str, Any]
    trace_id: str | None = None
    _root: Any = None
    _base_tags: list[str] = field(default_factory=list)
    _recorder: NodeRecorder = field(default_factory=NodeRecorder)

    def finish(self, result: dict[str, Any], *, first_token_ms: int | None = None) -> None:
        if self._root is None:
            return
        try:
            nodes = self._recorder.nodes
            summary = _turn_summary(result, nodes)
            answer = _answer(result)
            self._root.update(
                output={"role": "assistant", "content": answer} if answer else None,
                metadata=mask_sensitive(data=summary),
            )
            # propagate_attributes grava no span corrente, que aqui é o raiz do turno.
            with propagate_attributes(
                tags=[*self._base_tags, *_turn_tags(summary)],
                metadata={
                    key: mask_text(str(summary[key]))
                    for key in _TRACE_METADATA_KEYS
                    if key in summary
                },
            ):
                pass
            client = _get_client()
            for name, value, data_type in _turn_scores(
                result, nodes, summary, first_token_ms
            ):
                client.create_score(
                    trace_id=self.trace_id,
                    name=name,
                    value=value,
                    data_type=data_type,
                )
        except Exception:  # noqa: BLE001
            logger.exception("langfuse finish falhou trace=%s", self.trace_id)


@contextmanager
def langfuse_turn(
    run_config: dict[str, Any],
    *,
    assistant_id: str,
    session_id: str,
    message_id: str | None,
    message: str,
) -> Iterator[LangfuseTurn]:
    """Span raiz do turno; `run_config` do turno ganha o CallbackHandler, se ativo."""
    if not config.is_langfuse_active():
        yield LangfuseTurn(run_config=run_config)
        return
    try:
        client = _get_client()
        handler = CallbackHandler(public_key=config.LANGFUSE_PUBLIC_KEY)
        trace_id = Langfuse.create_trace_id(seed=message_id)
    except Exception:  # noqa: BLE001
        logger.exception("langfuse indisponivel session=%s", session_id)
        yield LangfuseTurn(run_config=run_config)
        return

    recorder = NodeRecorder()
    base_tags = ["the.ia", f"assistant:{assistant_id}"]
    turn = LangfuseTurn(
        run_config={
            **run_config,
            "callbacks": [*(run_config.get("callbacks") or []), handler, recorder],
        },
        trace_id=trace_id,
        _base_tags=base_tags,
        _recorder=recorder,
    )
    # Tags só no raiz e só no fim: o Langfuse fixa as tags do trace pela primeira
    # observação recebida, e os spans filhos são exportados antes do raiz.
    # Input/output em formato role/content: a tela de Sessions só monta o chat assim.
    seed_token = _seeded_trace_id.set(int(trace_id, 16))
    try:
        with client.start_as_current_observation(
            name="the.ia",
            as_type="agent",
            input=[{"role": "user", "content": message}],
        ) as root, propagate_attributes(
            session_id=session_id,
            trace_name=f"the.ia:{assistant_id}",
        ):
            _seeded_trace_id.reset(seed_token)
            turn._root = root
            try:
                yield turn
            except Exception as exc:
                root.update(level="ERROR", status_message=str(exc))
                with propagate_attributes(tags=[*base_tags, "erro"]):
                    pass
                raise
    finally:
        if _seeded_trace_id.get() is not None:
            _seeded_trace_id.reset(seed_token)


def score_feedback(
    *,
    message_id: str,
    feedback: Literal["positive", "negative"] | None,
    reason: str | None,
    reason_text: str | None,
) -> bool:
    """Grava like/dislike no trace da mensagem; reenvio sobrescreve a nota anterior."""
    if feedback is None or not config.is_langfuse_active():
        return False
    try:
        trace_id = Langfuse.create_trace_id(seed=message_id)
        _get_client().create_score(
            trace_id=trace_id,
            score_id=f"{trace_id}-{_FEEDBACK_SCORE}",
            name=_FEEDBACK_SCORE,
            value=1 if feedback == "positive" else 0,
            data_type="BOOLEAN",
            comment=mask_text(reason_text) if reason_text else None,
            metadata={"reason": reason} if reason else None,
        )
    except Exception:  # noqa: BLE001
        logger.exception("langfuse feedback falhou message=%s", message_id)
        return False
    return True


def _answer(result: dict[str, Any]) -> str | None:
    messages = result.get("messages") or []
    if messages and isinstance(messages[-1], AIMessage):
        content = messages[-1].content
        return content if isinstance(content, str) else str(content)
    return None


def _route_choice(decision: dict[str, Any]) -> str | None:
    route = decision.get("route")
    if isinstance(route, dict):
        route = route.get("choice")
    return route if isinstance(route, str) else None


def _turn_summary(result: dict[str, Any], nodes: set[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if "router_agent" in nodes:
        decision = result.get("decision") or {}
        summary.update(
            route=_route_choice(decision),
            router_source=decision.get("source"),
            router_confidence=decision.get("confidence"),
        )
    flow = next(
        (
            name
            for name in (result.get("active_flow"), result.get("service_target"))
            if name and name in nodes
        ),
        None,
    )
    if flow:
        summary.update(flow=flow, flow_step=result.get("flow_step"))
        if not summary.get("route"):
            summary["route"] = "flow"
    if "rag_subgraph" in nodes:
        rag = result.get("rag_result") or {}
        summary.update(
            collection_name=result.get("collection_name"),
            search_attempts=rag.get("search_attempts"),
            retrieved_chunks=rag.get("retrieved_chunk_count"),
            citations=len(result.get("citations") or []),
            judge_action=rag.get("judge_action"),
            judge=rag.get("judge"),
            retrieval_metrics=result.get("retrieval_metrics"),
            search_history=result.get("search_history"),
        )
    if "fallback_agent" in nodes:
        summary.update(
            fallback=True,
            fallback_reason=result.get("fallback_reason"),
            fallback_source=result.get("fallback_source"),
        )
    return {key: value for key, value in summary.items() if value is not None}


def _turn_tags(summary: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    if summary.get("route"):
        tags.append(f"route:{summary['route']}")
    if summary.get("flow"):
        tags.append(f"flow:{summary['flow']}")
    if summary.get("fallback"):
        tags.append("fallback")
    return tags


def _turn_scores(
    result: dict[str, Any],
    nodes: set[str],
    summary: dict[str, Any],
    first_token_ms: int | None,
) -> list[tuple[str, float, str]]:
    scores: list[tuple[str, float, str]] = [
        ("fallback", int(bool(summary.get("fallback"))), "BOOLEAN"),
    ]
    confidence = summary.get("router_confidence")
    if isinstance(confidence, int | float):
        scores.append(("router_confianca", float(confidence), "NUMERIC"))
    if "rag_subgraph" in nodes:
        no_results = result.get("fallback_reason") == _RAG_NO_RESULTS
        scores.append(("rag_sem_resultado", int(no_results), "BOOLEAN"))
        scores.append(("tem_citacao", int(summary.get("citations", 0) > 0), "BOOLEAN"))
        judge = summary.get("judge") or {}
        if isinstance(judge.get("grounded"), bool):
            scores.append(("juiz_fundamentada", int(judge["grounded"]), "BOOLEAN"))
        if isinstance(judge.get("answers_question"), bool):
            scores.append(("juiz_responde", int(judge["answers_question"]), "BOOLEAN"))
        if isinstance(judge.get("confidence"), int | float):
            scores.append(("juiz_confianca", float(judge["confidence"]), "NUMERIC"))
    if first_token_ms is not None:
        scores.append(("primeiro_token_ms", first_token_ms, "NUMERIC"))
    return scores


def flush_langfuse() -> None:
    if _client is None:
        return
    try:
        _client.flush()
    except Exception:  # noqa: BLE001
        logger.exception("langfuse flush falhou")
