from langgraph.graph import END
from graph.state import MultiAgentState


def build_service_caller_edges(flow_names: str) -> dict:
    edges = {"tools": "tools_node", "end": END}
    for name in flow_names:
        edges[name] = name
    return edges


def route_from_service_caller(state: MultiAgentState, allowed_flows: str) -> str:
    target = state.get("service_target")

    if target and target in allowed_flows:
        return target

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"

    return "end"
