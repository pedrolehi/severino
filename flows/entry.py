from graph.state import MultiAgentState


def route_entry(state: MultiAgentState) -> str:
    if state.get("active_flow"):
        return state["active_flow"]
    return "router"


def build_entry_edges(flow_names: str) -> dict[str, str]:
    edges: dict[str, str] = {
        "router": "router_agent",
    }

    for name in flow_names:
        edges[name] = name

    return edges
