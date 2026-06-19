from graph.state import MultiAgentState
from flows.registry import FLOWS


def route_entry(state: MultiAgentState) -> str:
    if state.get("active_flow"):
        return state["active_flow"]
    return "router"


def build_entry_edges() -> dict[str, str]:
    edges: dict[str, str] = {
        "router": "router_agent",
    }

    for name in FLOWS:
        edges[name] = name

    return edges
