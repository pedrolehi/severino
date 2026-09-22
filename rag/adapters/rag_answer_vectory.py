"""Cliente do pipeline RAG search-vectory (POST /rag/answer)."""

from __future__ import annotations

from typing import Any

from rag.http_client import VectoryHttpError, post_json

DEFAULT_TOP_K = 8
DEFAULT_MAX_QUERIES = 2
DEFAULT_MAX_MERGED_CHUNKS = 12
DEFAULT_SEARCH_BUFFER = 1
RAG_ANSWER_TIMEOUT_S = 120.0


def build_rag_answer_payload(
    *,
    query: str,
    collection_name: str,
    top_k: int = DEFAULT_TOP_K,
    max_queries: int = DEFAULT_MAX_QUERIES,
    max_merged_chunks: int = DEFAULT_MAX_MERGED_CHUNKS,
    search_buffer: int = DEFAULT_SEARCH_BUFFER,
    conversation: list[dict[str, str]] | None = None,
    session_id: str | None = None,
    agent_id: str | None = None,
    persist_log: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query.strip(),
        "collection_name": collection_name,
        "top_k": top_k,
        "max_queries": max_queries,
        "max_merged_chunks": max_merged_chunks,
        "search_buffer": search_buffer,
        "source": "rag_agent",
        "persist_log": persist_log,
    }
    if conversation:
        payload["conversation"] = conversation
    if session_id:
        payload["session_id"] = session_id
    if agent_id:
        payload["agent_id"] = agent_id
    return payload


def call_rag_answer(
    *,
    query: str,
    collection_name: str,
    top_k: int = DEFAULT_TOP_K,
    max_queries: int = DEFAULT_MAX_QUERIES,
    max_merged_chunks: int = DEFAULT_MAX_MERGED_CHUNKS,
    search_buffer: int = DEFAULT_SEARCH_BUFFER,
    conversation: list[dict[str, str]] | None = None,
    session_id: str | None = None,
    agent_id: str | None = None,
    persist_log: bool = True,
    base_url: str | None = None,
    timeout: float = RAG_ANSWER_TIMEOUT_S,
) -> dict[str, Any]:
    """POST /rag/answer. Levanta VectoryHttpError em falha HTTP."""
    payload = build_rag_answer_payload(
        query=query,
        collection_name=collection_name,
        top_k=top_k,
        max_queries=max_queries,
        max_merged_chunks=max_merged_chunks,
        search_buffer=search_buffer,
        conversation=conversation,
        session_id=session_id,
        agent_id=agent_id,
        persist_log=persist_log,
    )
    return post_json(
        "rag/answer",
        payload,
        base_url=base_url,
        timeout=timeout,
    )


__all__ = [
    "RAG_ANSWER_TIMEOUT_S",
    "VectoryHttpError",
    "build_rag_answer_payload",
    "call_rag_answer",
]
