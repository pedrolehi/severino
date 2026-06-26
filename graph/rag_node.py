from __future__ import annotations

from langchain_core.messages import HumanMessage

from graph.state import MultiAgentState
from rag.pipeline import run_rag_subgraph


def rag_subgraph_node(state: MultiAgentState) -> dict:
    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id não encontrado no estado")

    last_message = state["messages"][-1]
    if not isinstance(last_message, HumanMessage):
        raise ValueError("Última mensagem deve ser do usuário para RAG")

    content = last_message.content
    query = content if isinstance(content, str) else str(content)
    print(f"[RAG Subgraph] assistant={assistant_id}, query={query[:80]!r}...")

    result = run_rag_subgraph(assistant_id=assistant_id, query=query)
    update: dict = {
        "query": query,
        "search_query": result.get("search_query"),
        "search_attempt": result.get("search_attempt"),
        "search_history": result.get("search_history"),
        "collection_name": result.get("collection_name"),
        "chunks": result.get("chunks"),
        "citations": result.get("citations"),
        "retrieval_metrics": result.get("retrieval_metrics"),
        "rag_result": result.get("rag_result"),
        "fallback_reason": result.get("fallback_reason"),
        "fallback_source": result.get("fallback_source"),
        "fallback_hint": result.get("fallback_hint"),
    }
    if result.get("messages"):
        update["messages"] = result["messages"]
    return update
