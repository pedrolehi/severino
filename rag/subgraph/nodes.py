from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from assistants.registry import get_assistant_by_id
from core.config import APP_ENV
from core.llm import llm
from rag.adapters.search_vectory import SearchVectoryAdapter
from rag.policy import RagPolicy, resolve_rag_policy
from rag.citations import build_citations, chunks_to_retrieval_payload
from rag.ports import RetrievedChunk
from rag.project_store import resolve_collection_name
from rag.subgraph.models import JudgeVerdictModel
from rag.subgraph.state import RagSubgraphState

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_search_adapter = SearchVectoryAdapter()
_judge_llm = llm.with_structured_output(JudgeVerdictModel)


def _load_policy(state: RagSubgraphState) -> RagPolicy:
    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id ausente no state do subgrafo RAG")
    return resolve_rag_policy(get_assistant_by_id(assistant_id))


def _chunk_to_dict(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "content": chunk.content,
        "distance": chunk.distance,
        "adjusted_score": chunk.adjusted_score,
        "similarity": chunk.similarity,
        "metadata": chunk.metadata,
        "source": chunk.source,
    }


def _chunk_from_dict(data: dict[str, Any]) -> RetrievedChunk:
    adjusted = data.get("adjusted_score")
    distance_raw = data.get("distance")
    if distance_raw is None:
        distance_raw = data.get("score", 0)
    source = data.get("source")
    return RetrievedChunk(
        id=str(data.get("id", "")),
        content=str(data.get("content", "")),
        distance=float(distance_raw),
        metadata=dict(data.get("metadata") or {}),
        similarity=float(data.get("similarity", 0)),
        adjusted_score=float(adjusted) if adjusted is not None else None,
        source=dict(source) if isinstance(source, dict) else None,
    )


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(nenhum trecho encontrado)"

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        filename = (
            chunk.metadata.get("filename")
            or chunk.metadata.get("document_id")
            or "—"
        )
        parts.append(
            f"[{index}] (id={chunk.id}, sim={chunk.similarity:.2f}, arquivo={filename})\n"
            f"{chunk.content.strip()}"
        )
    return "\n\n".join(parts)


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _judge_rejection_code(verdict: dict[str, Any]) -> str | None:
    if verdict.get("action") != "fallback":
        return None
    return "ungrounded" if not verdict.get("grounded") else "low_quality"


def _build_rag_result_payload(
    state: RagSubgraphState,
    *,
    draft_answer: str | None = None,
    verdict: dict[str, Any] | None = None,
    fallback_reason: str | None = None,
    fallback_hint: str | None = None,
) -> dict[str, Any]:
    chunks = [_chunk_from_dict(item) for item in (state.get("chunks") or [])]
    attempt = int(state.get("search_attempt") or 0) + 1
    query = (state.get("query") or "").strip()
    search_query = (state.get("search_query") or query).strip()
    verdict = verdict or state.get("judge_verdict") or {}
    judge_action = str(verdict["action"]) if verdict.get("action") else None

    rag_result: dict[str, Any] = {
        "query": query,
        "collection_name": state.get("collection_name") or "",
        "search_attempts": attempt,
        "judge_action": judge_action,
        "retrieval_metrics": state.get("retrieval_metrics"),
        "retrieved_chunk_count": len(chunks),
        "top_k": chunks_to_retrieval_payload(chunks),
    }

    if search_query.lower() != query.lower():
        rag_result["retrieval_query"] = search_query

    if draft_answer:
        rag_result["draft_answer"] = draft_answer
        rag_result["citations"] = build_citations(draft_answer, chunks)

    if judge_action == "fallback":
        rag_result["judge"] = {
            "grounded": verdict.get("grounded"),
            "answers_question": verdict.get("answers_question"),
            "confidence": verdict.get("confidence"),
            "issues": list(verdict.get("issues") or []),
            "fallback_hint": verdict.get("fallback_hint"),
            "rejection_code": _judge_rejection_code(verdict),
        }
    elif judge_action == "accept":
        rag_result["judge"] = {
            "grounded": verdict.get("grounded", True),
            "answers_question": verdict.get("answers_question", True),
            "confidence": verdict.get("confidence"),
            "issues": list(verdict.get("issues") or []),
        }

    resolved_fallback = fallback_reason or state.get("fallback_reason")
    resolved_hint = (
        fallback_hint if fallback_hint is not None else state.get("fallback_hint")
    )
    if resolved_fallback and str(resolved_fallback).startswith("rag_retrieval:"):
        rag_result["retrieval_failure"] = {
            "reason": resolved_fallback,
            "hint": resolved_hint,
        }

    return rag_result


def prepare_query(state: RagSubgraphState) -> dict[str, Any]:
    query = (state.get("query") or "").strip()
    if not query:
        raise ValueError("query ausente no state do subgrafo RAG")

    return {
        "search_query": query,
        "search_attempt": 0,
        "search_history": [],
        "fallback_reason": None,
        "fallback_source": None,
        "fallback_hint": None,
    }


def retrieve(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    collection_name = resolve_collection_name(policy.project_id, APP_ENV)
    search_query = (state.get("search_query") or state.get("query") or "").strip()
    attempt = int(state.get("search_attempt") or 0)

    chunks = _search_adapter.search(
        query=search_query,
        collection_name=collection_name,
        search_policy=policy.search,
    )

    history = list(state.get("search_history") or [])
    top_score = chunks[0].distance if chunks else 1.0
    top_similarity = chunks[0].similarity if chunks else 0.0
    history.append(
        {
            "attempt": attempt,
            "search_query": search_query,
            "top_score": top_score,
            "top_similarity": top_similarity,
            "chunk_count": len(chunks),
            "chunk_ids": [chunk.id for chunk in chunks[:5]],
        }
    )

    metrics = {
        "top_distance": top_score,
        "top_similarity": top_similarity,
    }

    return {
        "collection_name": collection_name,
        "chunks": [_chunk_to_dict(chunk) for chunk in chunks],
        "retrieval_metrics": metrics,
        "search_history": history,
    }


def retrieval_gate(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    chunks = [_chunk_from_dict(item) for item in (state.get("chunks") or [])]
    attempt = int(state.get("search_attempt") or 0)
    max_attempts = policy.quality.max_search_attempts

    if not chunks:
        if attempt + 1 < max_attempts:
            return {
                "retry_reason": "Nenhum trecho encontrado na busca.",
                "judge_verdict": {
                    "action": "retry_search",
                    "rewritten_query": None,
                },
            }
        return {
            "fallback_reason": "rag_retrieval:no_results",
            "fallback_source": "rag_retrieval",
            "fallback_hint": "Não há trechos indexados para esta pergunta.",
            "rag_result": _build_rag_result_payload(
                state,
                fallback_reason="rag_retrieval:no_results",
                fallback_hint="Não há trechos indexados para esta pergunta.",
            ),
        }

    return {"retry_reason": None, "judge_verdict": None}


def route_after_retrieval_gate_node(state: RagSubgraphState) -> str:
    if state.get("fallback_reason"):
        return "end_fallback"
    verdict = state.get("judge_verdict") or {}
    if verdict.get("action") == "retry_search":
        return "rewrite_query"
    return "build_context"


def build_context(state: RagSubgraphState) -> dict[str, Any]:
    chunks = [_chunk_from_dict(item) for item in (state.get("chunks") or [])]
    return {
        "context_text": _format_context(chunks),
        "judge_verdict": None,
    }


def generate(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    query = (state.get("query") or "").strip()
    context = state.get("context_text") or "(nenhum trecho encontrado)"
    prompt_template = _read_prompt(policy.prompt_path)
    prompt = prompt_template.format(context=context, query=query)

    response = llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=query),
        ]
    )
    content = response.content
    answer = content if isinstance(content, str) else str(content)
    return {"draft_answer": answer}


def judge(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    if not policy.quality.judge_enabled:
        return {
            "judge_verdict": {
                "action": "accept",
                "grounded": True,
                "answers_question": True,
                "confidence": 1.0,
                "issues": [],
            }
        }

    attempt = int(state.get("search_attempt") or 0)
    max_attempts = policy.quality.max_search_attempts
    can_retry = (
        policy.quality.allow_judge_retry and (attempt + 1) < max_attempts
    )

    prompt_template = _read_prompt(policy.judge_prompt_path)
    prompt = prompt_template.format(
        query=(state.get("query") or "").strip(),
        context=state.get("context_text") or "",
        answer=state.get("draft_answer") or "",
        search_attempt=attempt + 1,
        max_attempts=max_attempts,
    )

    verdict = _judge_llm.invoke([SystemMessage(content=prompt)])

    if verdict.action == "retry_search" and not can_retry:
        verdict = verdict.model_copy(
            update={
                "action": "fallback",
                "fallback_hint": verdict.fallback_hint
                or "Esgotadas as tentativas de busca.",
            }
        )

    if verdict.action == "retry_search" and not verdict.rewritten_query:
        verdict = verdict.model_copy(
            update={
                "retry_reason": verdict.retry_reason
                or "A resposta não ficou bem sustentada nos trechos.",
            }
        )

    result: dict[str, Any] = {"judge_verdict": verdict.model_dump()}
    if verdict.action == "fallback":
        fallback_reason = "rag_judge:" + (
            "ungrounded" if not verdict.grounded else "low_quality"
        )
        result.update(
            {
                "fallback_reason": fallback_reason,
                "fallback_source": "rag_judge",
                "fallback_hint": verdict.fallback_hint,
                "rag_result": _build_rag_result_payload(
                    state,
                    draft_answer=state.get("draft_answer"),
                    verdict=verdict.model_dump(),
                    fallback_reason=fallback_reason,
                    fallback_hint=verdict.fallback_hint,
                ),
            }
        )
    elif verdict.action == "retry_search":
        result["retry_reason"] = verdict.retry_reason

    return result


def rewrite_query(state: RagSubgraphState) -> dict[str, Any]:
    attempt = int(state.get("search_attempt") or 0) + 1
    previous_query = (state.get("search_query") or state.get("query") or "").strip()
    verdict = state.get("judge_verdict") or {}
    retry_reason = (
        state.get("retry_reason")
        or verdict.get("retry_reason")
        or "Melhorar cobertura da busca."
    )
    rewritten = (verdict.get("rewritten_query") or "").strip()

    if not rewritten:
        rewrite_template = _read_prompt(PROMPTS_DIR / "rewrite.txt")
        rewrite_prompt = rewrite_template.format(
            retry_reason=retry_reason,
            previous_query=previous_query,
        )
        response = llm.invoke([HumanMessage(content=rewrite_prompt)])
        content = response.content
        rewritten = (content if isinstance(content, str) else str(content)).strip()

    if rewritten.lower() == previous_query.lower():
        rewritten = f"{previous_query} procedimento documentação"

    return {
        "search_query": rewritten,
        "search_attempt": attempt,
        "judge_verdict": None,
        "draft_answer": None,
        "fallback_reason": None,
        "fallback_source": None,
        "fallback_hint": None,
        "chunks": [],
    }


def route_after_judge_node(state: RagSubgraphState) -> str:
    verdict = state.get("judge_verdict") or {}
    action = verdict.get("action")
    if action == "accept":
        return "pack_response"
    if action == "fallback" and (state.get("draft_answer") or "").strip():
        return "pack_response"
    if action == "retry_search":
        return "rewrite_query"
    return "mark_fallback"


def pack_response(state: RagSubgraphState) -> dict[str, Any]:
    verdict = state.get("judge_verdict") or {}
    draft_answer = (state.get("draft_answer") or "").strip()

    from langchain_core.messages import AIMessage

    return {
        "rag_result": _build_rag_result_payload(
            state,
            draft_answer=draft_answer,
            verdict=verdict,
        ),
        "messages": [AIMessage(content=draft_answer)],
    }


def mark_fallback(state: RagSubgraphState) -> dict[str, Any]:
    if state.get("fallback_reason"):
        return {}
    return {
        "fallback_reason": "rag_retrieval:unknown",
        "fallback_source": "rag_retrieval",
    }
