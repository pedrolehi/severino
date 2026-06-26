from functools import partial
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from agents.router_agent import router_agent
from agents.service_caller_agent import service_caller_agent
from agents.fallback_agent import fallback_agent
from assistants.capabilities import resolve_capabilities
from core.database.memory import get_memory
from flows.entry import build_entry_edges, route_entry
from flows.registry import register_flow_graphs
from graph.rag_node import rag_subgraph_node
from graph.routing.router import ROUTER_EDGES, route_from_decision
from graph.routing.rag_exit import route_after_rag
from graph.routing.service_caller import (
    build_service_caller_edges,
    route_from_service_caller,
)
from graph.state import MultiAgentState


def build_graph(assistant_id: str):
    caps = resolve_capabilities(assistant_id)
    flow_names = frozenset(caps.flows.keys())

    workflow = StateGraph(MultiAgentState)

    workflow.add_node("router_agent", router_agent)
    workflow.add_node("service_caller_agent", service_caller_agent)
    workflow.add_node("tools_node", ToolNode(list(caps.tools)))
    workflow.add_node("rag_subgraph", rag_subgraph_node)
    workflow.add_node("fallback_agent", fallback_agent)

    register_flow_graphs(workflow, caps.flows)
    workflow.add_conditional_edges(START, route_entry, build_entry_edges(flow_names))
    workflow.add_conditional_edges(
        "router_agent",
        route_from_decision,
        ROUTER_EDGES,
    )

    workflow.add_conditional_edges(
        "service_caller_agent",
        partial(route_from_service_caller, allowed_flows=flow_names),
        build_service_caller_edges(flow_names),
    )
    workflow.add_conditional_edges(
        "rag_subgraph",
        route_after_rag,
        {
            "fallback_agent": "fallback_agent",
            "end": END,
        },
    )
    workflow.add_edge("tools_node", END)
    workflow.add_edge("fallback_agent", END)
    return workflow.compile(checkpointer=get_memory())
