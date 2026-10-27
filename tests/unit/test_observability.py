from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from core import config, observability

TRACE_ID = "0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _reset_client() -> Iterator[None]:
    observability.reset_langfuse_client()
    yield
    observability.reset_langfuse_client()


class _Fakes:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(config, "LANGFUSE_ENABLED", True)
        monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk-test")
        monkeypatch.setattr(config, "LANGFUSE_HOST", "https://langfuse.local")
        self.client_cls = MagicMock(name="Langfuse")
        self.client_cls.create_trace_id.return_value = TRACE_ID
        self.handler_cls = MagicMock(name="CallbackHandler")
        self.propagate = MagicMock(name="propagate_attributes")
        monkeypatch.setattr(observability, "Langfuse", self.client_cls)
        monkeypatch.setattr(observability, "CallbackHandler", self.handler_cls)
        monkeypatch.setattr(observability, "propagate_attributes", self.propagate)

    @property
    def client(self) -> MagicMock:
        return self.client_cls.return_value

    @property
    def root(self) -> MagicMock:
        return self.client.start_as_current_observation.return_value.__enter__.return_value

    def scores(self) -> dict[str, dict[str, Any]]:
        return {
            call.kwargs["name"]: call.kwargs
            for call in self.client.create_score.call_args_list
        }

    def propagated(self, key: str) -> list[Any]:
        return [
            call.kwargs[key] for call in self.propagate.call_args_list if key in call.kwargs
        ]


def _turn(**overrides: Any):
    kwargs: dict[str, Any] = {
        "assistant_id": "intranet",
        "session_id": "s1",
        "message_id": "msg-1",
        "message": "como pedir férias?",
    }
    kwargs.update(overrides)
    run_config = kwargs.pop("run_config", {"configurable": {"thread_id": "intranet:s1"}})
    return observability.langfuse_turn(run_config, **kwargs)


def _ran(turn: observability.LangfuseTurn, *nodes: str) -> None:
    recorder = next(
        cb
        for cb in turn.run_config["callbacks"]
        if isinstance(cb, observability.NodeRecorder)
    )
    for node in nodes:
        recorder.on_chain_start({}, {}, run_id=uuid4(), metadata={"langgraph_node": node})


def test_langfuse_inativo_devolve_config_intacto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LANGFUSE_ENABLED", True)
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "")

    with _turn() as turn:
        turn.finish({"messages": [AIMessage(content="oi")]})

    assert turn.trace_id is None
    assert turn.run_config == {"configurable": {"thread_id": "intranet:s1"}}


def test_langfuse_desligado_por_flag_mesmo_com_chaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)
    monkeypatch.setattr(config, "LANGFUSE_ENABLED", False)

    with _turn() as turn:
        pass

    assert "callbacks" not in turn.run_config
    fakes.client_cls.assert_not_called()


def test_turno_usa_trace_id_derivado_do_message_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)

    with _turn(run_config={"configurable": {"thread_id": "t"}, "metadata": {"invoke_t0": 1.5}}) as turn:
        pass

    fakes.client_cls.create_trace_id.assert_called_once_with(seed="msg-1")
    assert turn.trace_id == TRACE_ID
    kwargs = fakes.client.start_as_current_observation.call_args.kwargs
    assert kwargs["input"] == [{"role": "user", "content": "como pedir férias?"}]
    fakes.handler_cls.assert_called_once_with(public_key="pk-test")
    assert turn.run_config["callbacks"][0] is fakes.handler_cls.return_value
    assert turn.run_config["configurable"] == {"thread_id": "t"}
    assert turn.run_config["metadata"] == {"invoke_t0": 1.5}


def test_turno_propaga_sessao_sem_usuario_e_tags_so_no_fim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)

    with _turn() as turn:
        first = fakes.propagate.call_args_list[0].kwargs
        turn.finish({"messages": []})

    assert first["session_id"] == "s1"
    assert first["trace_name"] == "the.ia:intranet"
    assert "user_id" not in first
    assert "tags" not in first
    assert fakes.propagated("tags") == [["the.ia", "assistant:intranet"]]


def test_cliente_langfuse_criado_uma_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    fakes = _Fakes(monkeypatch)

    with _turn(message_id="a"):
        pass
    with _turn(message_id="b"):
        pass

    fakes.client_cls.assert_called_once()
    assert fakes.client_cls.call_args.kwargs["mask"] is observability.mask_sensitive
    assert isinstance(
        fakes.client_cls.call_args.kwargs["id_generator"], observability.SeededIdGenerator
    )


def test_raiz_do_turno_nasce_sem_pai_com_trace_id_do_message_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com `trace_context` o SDK inventa um pai e a tela de Sessions perde a conversa."""
    fakes = _Fakes(monkeypatch)
    generator = observability.SeededIdGenerator()
    seen: list[int] = []
    root_cm = fakes.client.start_as_current_observation.return_value

    def _start(**kwargs: Any) -> MagicMock:
        seen.append(generator.generate_trace_id())
        return root_cm

    fakes.client.start_as_current_observation.side_effect = _start

    with _turn():
        pass

    kwargs = fakes.client.start_as_current_observation.call_args.kwargs
    assert "trace_context" not in kwargs
    assert seen == [int(TRACE_ID, 16)]
    assert generator.generate_trace_id() != int(TRACE_ID, 16)


def test_finish_turno_rag_grava_resposta_tags_e_notas_do_juiz(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)
    result = {
        "decision": {"route": "rag", "confidence": 0.91, "source": "jev"},
        "collection_name": "intranet_hml",
        "citations": [{"id": "c1"}],
        "retrieval_metrics": {"top_distance": 0.2, "top_similarity": 0.8},
        "search_history": [{"attempt": 0, "search_query": "férias"}],
        "rag_result": {
            "search_attempts": 1,
            "retrieved_chunk_count": 5,
            "judge_action": "accept",
            "judge": {"grounded": True, "answers_question": False, "confidence": 0.7},
        },
        "messages": [HumanMessage(content="como pedir férias?"), AIMessage(content="Pelo portal.")],
    }

    with _turn() as turn:
        _ran(turn, "router_agent", "rag_subgraph")
        turn.finish(result, first_token_ms=840)

    update = fakes.root.update.call_args.kwargs
    assert update["output"] == {"role": "assistant", "content": "Pelo portal."}
    assert update["metadata"]["route"] == "rag"
    assert update["metadata"]["citations"] == 1
    assert update["metadata"]["search_history"] == [{"attempt": 0, "search_query": "férias"}]
    assert fakes.propagated("tags")[-1] == ["the.ia", "assistant:intranet", "route:rag"]
    assert fakes.propagated("metadata")[-1]["judge_action"] == "accept"

    scores = fakes.scores()
    assert {name: s["value"] for name, s in scores.items()} == {
        "fallback": 0,
        "router_confianca": 0.91,
        "rag_sem_resultado": 0,
        "tem_citacao": 1,
        "juiz_fundamentada": 1,
        "juiz_responde": 0,
        "juiz_confianca": 0.7,
        "primeiro_token_ms": 840,
    }
    assert all(s["trace_id"] == TRACE_ID for s in scores.values())
    assert scores["fallback"]["data_type"] == "BOOLEAN"


def test_finish_turno_de_flow_ignora_decisao_e_rag_de_turnos_anteriores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)
    stale = {
        "decision": {"route": "rag", "confidence": 0.9},
        "fallback_reason": "rag_retrieval:no_results",
        "citations": [{"id": "velha"}],
        "rag_result": {"judge_action": "fallback"},
        "active_flow": "segunda_via_boleto",
        "flow_step": "collect_form",
        "messages": [AIMessage(content="Informe o CPF.")],
    }

    with _turn() as turn:
        _ran(turn, "segunda_via_boleto")
        turn.finish(stale)

    assert fakes.propagated("tags")[-1] == [
        "the.ia",
        "assistant:intranet",
        "route:flow",
        "flow:segunda_via_boleto",
    ]
    metadata = fakes.root.update.call_args.kwargs["metadata"]
    assert metadata["flow_step"] == "collect_form"
    assert "judge_action" not in metadata
    assert "fallback_reason" not in metadata
    assert {name: s["value"] for name, s in fakes.scores().items()} == {"fallback": 0}


def test_finish_turno_de_fallback_marca_tag_e_nota(monkeypatch: pytest.MonkeyPatch) -> None:
    fakes = _Fakes(monkeypatch)
    result = {
        "decision": {"route": "rag", "confidence": 0.6},
        "fallback_reason": "rag_retrieval:no_results",
        "rag_result": {"retrieved_chunk_count": 0},
        "messages": [AIMessage(content="Não encontrei.")],
    }

    with _turn() as turn:
        _ran(turn, "router_agent", "rag_subgraph", "fallback_agent")
        turn.finish(result)

    assert "fallback" in fakes.propagated("tags")[-1]
    scores = fakes.scores()
    assert scores["fallback"]["value"] == 1
    assert scores["rag_sem_resultado"]["value"] == 1
    assert scores["tem_citacao"]["value"] == 0


def test_erro_no_turno_marca_trace_como_erro_e_repropaga(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)

    with pytest.raises(RuntimeError, match="jev fora"), _turn():
        raise RuntimeError("jev fora")

    fakes.root.update.assert_called_once_with(level="ERROR", status_message="jev fora")
    assert fakes.propagated("tags") == [["the.ia", "assistant:intranet", "erro"]]


def test_feedback_positivo_vira_nota_no_trace_da_mensagem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)

    recorded = observability.score_feedback(
        message_id="msg-1",
        feedback="positive",
        reason=None,
        reason_text=None,
    )

    assert recorded is True
    fakes.client_cls.create_trace_id.assert_called_with(seed="msg-1")
    score = fakes.client.create_score.call_args.kwargs
    assert score["trace_id"] == TRACE_ID
    assert score["name"] == "feedback_usuario"
    assert score["value"] == 1
    assert score["data_type"] == "BOOLEAN"
    assert score["score_id"] == f"{TRACE_ID}-feedback_usuario"


def test_feedback_negativo_leva_motivo_e_texto_mascarado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)

    observability.score_feedback(
        message_id="msg-1",
        feedback="negative",
        reason="other",
        reason_text="meu cpf 443.456.428-50 não foi aceito",
    )

    score = fakes.client.create_score.call_args.kwargs
    assert score["value"] == 0
    assert score["comment"] == "meu cpf *** não foi aceito"
    assert score["metadata"] == {"reason": "other"}


def test_feedback_removido_ou_langfuse_inativo_nao_grava(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fakes = _Fakes(monkeypatch)
    assert observability.score_feedback(
        message_id="msg-1", feedback=None, reason=None, reason_text=None
    ) is False
    fakes.client.create_score.assert_not_called()

    monkeypatch.setattr(config, "LANGFUSE_ENABLED", False)
    assert observability.score_feedback(
        message_id="msg-1", feedback="positive", reason=None, reason_text=None
    ) is False


def test_mask_remove_pii_do_user_info_e_preserva_chapa() -> None:
    state = {
        "session_id": "s1",
        "user_info": {
            "chapa": "1142372",
            "unidade": "CAS",
            "cpf": "443.456.428-50",
            "pis": "12345678900",
            "email": "x@sp.senac.br",
            "data_nascimento": "01/01/1990",
        },
        "messages": [{"DADOS": {"CPF": "111", "NOME": "Fulano"}}],
    }

    masked = observability.mask_sensitive(data=state)

    assert masked["user_info"] == {
        "chapa": "1142372",
        "unidade": "CAS",
        "cpf": "***",
        "pis": "***",
        "email": "***",
        "data_nascimento": "***",
    }
    assert masked["messages"][0]["DADOS"] == {"CPF": "***", "NOME": "***"}
    assert state["user_info"]["cpf"] == "443.456.428-50"


def test_mask_cpf_e_email_digitados_no_texto() -> None:
    text = "Meu CPF é 443.456.428-50 (ou 44345642850), email Fulano.Tal@sp.senac.br"

    assert observability.mask_sensitive(data=text) == "Meu CPF é *** (ou ***), email ***"


def test_mask_cpf_dentro_de_mensagens_langchain() -> None:
    message = HumanMessage(content="cpf 443.456.428-50")

    masked = observability.mask_sensitive(data={"messages": [message]})

    assert masked["messages"][0].content == "cpf ***"
    assert message.content == "cpf 443.456.428-50"


def test_mask_preserva_ids_e_numeros_que_nao_sao_cpf() -> None:
    values = [
        "texto livre",
        "1142372",
        "c7d6195f-5b58-4880-8cfc-e7aba9cc6371",
        "7d6c195f5b58e8806cfce7aba9cc6371",
        "20261027164144",
    ]

    assert observability.mask_sensitive(data=values) == values
    assert observability.mask_sensitive(data=None) is None
    assert observability.mask_sensitive(data=[1, "a"]) == [1, "a"]
