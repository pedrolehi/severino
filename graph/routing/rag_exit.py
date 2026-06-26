from graph.state import MultiAgentState


def route_after_rag(state: MultiAgentState) -> str:
    if state.get("fallback_reason"):
        return "fallback_agent"
    return "end"
