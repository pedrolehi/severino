from graph.state import MultiAgentState
from langgraph.graph import END

TOOL_CALLER_EDGES = {
    "tools": "tools_node",
    "end": END,
}


def route_from_tool_caller(state: MultiAgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "end"
