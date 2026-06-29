from graph.state import MultiAgentState


def route_after_rag(state: MultiAgentState) -> str:
    rag_result = state.get("rag_result") or {}
    if rag_result.get("draft_answer"):
        return "end"
    if state.get("fallback_reason"):
        return "fallback_agent"
    return "end"
