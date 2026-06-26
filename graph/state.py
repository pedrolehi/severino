from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    user_id: str | None
    session_id: str | None
    assistant_id: str | None

    # Roteamento
    decision: dict | None
    service_target: str | None
    active_flow: str | None
    flow_step: str | None
    flow_data: dict | None

    # RAG / fallback
    query: str | None
    search_query: str | None
    search_attempt: int | None
    search_history: list[dict[str, Any]] | None
    collection_name: str | None
    chunks: list[dict[str, Any]] | None
    citations: list[dict[str, Any]] | None
    retrieval_metrics: dict[str, Any] | None
    rag_result: dict[str, Any] | None
    fallback_reason: str | None
    fallback_source: str | None
    fallback_hint: str | None
