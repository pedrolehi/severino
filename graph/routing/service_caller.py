from langgraph.graph import END
from graph.state import MultiAgentState
from flows.registry import FLOWS


def build_service_caller_edges() -> dict:
    edges = {"tools": "tools_node", "end": END}
    for name in FLOWS:
        edges[name] = name
    return edges


def route_from_service_caller(state: MultiAgentState):
    target = state.get("service_target")

    if target and target in FLOWS:
        return target

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"

    return "end"


SERVICE_CALLER_EDGES = build_service_caller_edges()
