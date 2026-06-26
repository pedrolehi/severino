from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RagSubgraphState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]

    assistant_id: str
    query: str
    search_query: str
    search_attempt: int
    search_history: list[dict[str, Any]]

    collection_name: str
    chunks: list[dict[str, Any]]
    context_text: str
    retrieval_metrics: dict[str, Any]

    draft_answer: str
    judge_verdict: dict[str, Any]

    rag_result: dict[str, Any]
    fallback_reason: str | None
    fallback_source: str | None
    fallback_hint: str | None

    retry_reason: str | None
