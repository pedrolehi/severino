"""Executa RAG via pipeline search-vectory (não usa subgraph local retrieve/generate)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from assistants.registry import get_assistant_by_id
from core.config import APP_ENV, SEARCH_VECTORY_URL
from rag.adapters.rag_answer_vectory import VectoryHttpError, call_rag_answer
from rag.policy import resolve_rag_policy
from rag.project_store import resolve_assistant_collection
from rag.scoring import distance_to_similarity


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "")
    try:
        return float(text)
    except ValueError:
        return default


def _chunk_item_to_state(item: dict[str, Any]) -> dict[str, Any]:
    score = item.get("score")
    distance_raw = item.get("distance")
    if distance_raw is None:
        distance_raw = score if score is not None else 0.0
    distance = _as_float(distance_raw, 0.0)
    adjusted_raw = item.get("adjusted_score")
    metadata = dict(item.get("metadata") or {})
    similarity_raw = item.get("similarity")
    if similarity_raw is None:
        similarity = distance_to_similarity(distance)
    else:
        similarity = _as_float(similarity_raw, distance_to_similarity(distance))
        # UI às vezes manda "55.8%" (0-100); normaliza para 0-1
        if similarity > 1.0:
            similarity = similarity / 100.0
    return {
        "id": str(item.get("id", "")),
        "content": str(item.get("content", "")),
        "distance": distance,
        "similarity": similarity,
        "adjusted_score": (
            _as_float(adjusted_raw) if adjusted_raw is not None else None
        ),
        "metadata": metadata,
        "source": dict(item),
    }


def _map_pipeline_status(status: str) -> tuple[str | None, str | None, str | None]:
    """Retorna (fallback_reason, fallback_source, fallback_hint) ou (None, None, None)."""
    normalized = (status or "").strip().lower()
    if normalized in {"answered", "needs_clarification"}:
        return None, None, None
    if normalized == "no_evidence":
        return (
            "rag_pipeline:no_evidence",
            "rag_pipeline",
            "Pipeline não encontrou evidência suficiente nos documentos.",
        )
    if normalized == "blocked":
        return (
            "rag_pipeline:blocked",
            "rag_pipeline",
            "Pipeline bloqueou a resposta.",
        )
    if normalized == "rejected":
        return (
            "rag_pipeline:rejected",
            "rag_pipeline",
            "Judge do pipeline rejeitou a resposta.",
        )
    return (
        f"rag_pipeline:{normalized or 'unknown'}",
        "rag_pipeline",
        "Pipeline RAG retornou status sem resposta útil.",
    )


def run_rag_pipeline(
    *,
    assistant_id: str,
    query: str,
    app_env: str | None = None,
    session_id: str | None = None,
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Chama POST /rag/answer e devolve state compatível com rag_subgraph_node."""
    assistant = get_assistant_by_id(assistant_id)
    policy = resolve_rag_policy(assistant)
    env = (app_env or APP_ENV or "dev").strip().lower()
    collection_name = resolve_assistant_collection(
        project_id=policy.project_id,
        app_env=env,
        collection_name=policy.collection_name,
    )
    query_clean = query.strip()
    turns = list(conversation or [])

    print(
        f"[RAG pipeline] assistant={assistant_id} app_env={env} "
        f"collection={collection_name} url={SEARCH_VECTORY_URL}/rag/answer "
        f"q={query_clean[:80]!r} conversation_turns={len(turns)}"
    )

    try:
        body = call_rag_answer(
            query=query_clean,
            collection_name=collection_name,
            top_k=policy.search.top_k,
            search_buffer=max(1, int(policy.search.search_buffer or 1)),
            conversation=turns or None,
            session_id=session_id,
            agent_id=assistant_id,
            persist_log=True,
        )
    except VectoryHttpError as exc:
        print(f"[RAG pipeline] HTTP erro: {exc}")
        return {
            "query": query_clean,
            "app_env": env,
            "collection_name": collection_name,
            "chunks": [],
            "search_attempt": 0,
            "fallback_reason": "rag_pipeline:http_error",
            "fallback_source": "rag_pipeline",
            "fallback_hint": str(exc.detail),
            "rag_result": {
                "query": query_clean,
                "collection_name": collection_name,
                "pipeline": "rag_answer",
                "error": str(exc.detail),
            },
        }

    status = str(body.get("status") or "")
    raw_chunks = body.get("chunks") if isinstance(body.get("chunks"), list) else []
    chunks = [_chunk_item_to_state(item) for item in raw_chunks if isinstance(item, dict)]
    answer = (body.get("answer") or "").strip()
    clarification = (body.get("clarification_question") or "").strip()
    fallback_message = (body.get("fallback_message") or "").strip()

    print(
        f"[RAG pipeline] status={status} chunks={len(chunks)} "
        f"judge_ok={body.get('judge_ok')} log_id={body.get('log_id')!r} "
        f"llm={body.get('llm_model')!r}"
    )
    timings_ms = body.get("timings_ms")
    if isinstance(timings_ms, dict) and timings_ms:
        parts = [
            f"{key}={int(val)}ms"
            for key, val in timings_ms.items()
            if isinstance(val, (int, float))
        ]
        if parts:
            print(f"[RAG pipeline] timings: {', '.join(parts)}")

    draft = answer or clarification or ""
    fallback_reason, fallback_source, fallback_hint = _map_pipeline_status(status)

    if not draft and fallback_message and fallback_reason:
        fallback_hint = fallback_message
    elif not draft and not fallback_reason and body.get("success") is False:
        fallback_reason = "rag_pipeline:error"
        fallback_source = "rag_pipeline"
        fallback_hint = str(body.get("error") or fallback_message or "Pipeline falhou")

    if status == "needs_clarification" and not draft:
        draft = clarification or fallback_message

    rag_result: dict[str, Any] = {
        "query": query_clean,
        "collection_name": collection_name,
        "pipeline": "rag_answer",
        "status": status,
        "judge_ok": body.get("judge_ok"),
        "judge_action": (
            "accept"
            if status == "answered"
            else ("clarify" if status == "needs_clarification" else "fallback")
        ),
        "retrieved_chunk_count": len(chunks),
        "log_id": body.get("log_id"),
        "llm_model": body.get("llm_model"),
        "timings_ms": body.get("timings_ms"),
        "plan": body.get("plan"),
        "trace": body.get("trace"),
    }
    if draft:
        rag_result["draft_answer"] = draft

    result: dict[str, Any] = {
        "query": query_clean,
        "search_query": query_clean,
        "app_env": env,
        "collection_name": collection_name,
        "chunks": chunks,
        "search_attempt": 0,
        "rag_result": rag_result,
        "fallback_reason": fallback_reason,
        "fallback_source": fallback_source,
        "fallback_hint": fallback_hint,
    }
    if draft:
        result["messages"] = [AIMessage(content=draft)]
        # resposta útil → não manda pro fallback_agent
        if status in {"answered", "needs_clarification"}:
            result["fallback_reason"] = None
            result["fallback_source"] = None
            result["fallback_hint"] = None

    return result
