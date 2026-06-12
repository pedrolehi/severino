from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agents.router_agent import router_agent
from agents.tool_caller_agent import tool_caller_agent

from flows.entry import route_entry, build_entry_edges
from flows.registry import register_flow_graphs

from core.database.memory import get_memory

from graph.dummies import rag_agent, fallback_agent
from graph.routing.router import route_from_decision, ROUTER_EDGES
from graph.routing.tool_caller import route_from_tool_caller, TOOL_CALLER_EDGES
from graph.state import MultiAgentState

from tools import tools_list


workflow = StateGraph(MultiAgentState)

# Setar todos os nodes principais
workflow.add_node("router_agent", router_agent)
workflow.add_node("tool_caller_agent", tool_caller_agent)
workflow.add_node("tools_node", ToolNode(tools_list))
workflow.add_node("rag_agent", rag_agent)
workflow.add_node("fallback_agent", fallback_agent)

# Registrar todos os flows
register_flow_graphs(workflow)

# Início do turno sempre no router
workflow.add_conditional_edges(START, route_entry, build_entry_edges())

# Rotas de decisão
workflow.add_conditional_edges(
    "router_agent",
    route_from_decision,
    ROUTER_EDGES,
)

workflow.add_conditional_edges(
    "tool_caller_agent",
    route_from_tool_caller,
    TOOL_CALLER_EDGES,
)

# Fim de turnos específicos
workflow.add_edge("tools_node", END)
workflow.add_edge("rag_agent", END)
workflow.add_edge("fallback_agent", END)

memory = get_memory()
print(f"memory: {memory}")

app_graph = workflow.compile(checkpointer=memory)
