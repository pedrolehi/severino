from graph.state import MultiAgentState
from agents.router_agent.node import Route, RouteDecision

ROUTER_ROUTE_TO_NODE = {
    Route.RAG: "rag_subgraph",
    Route.SERVICES: "service_caller_agent",
    Route.FALLBACK: "fallback_agent",
}


def route_from_decision(state: MultiAgentState) -> str:
    raw_decision = state.get("decision")
    if not raw_decision:
        return Route.FALLBACK.value
    return RouteDecision.model_validate(raw_decision).route.value


ROUTER_EDGES = {route.value: node for route, node in ROUTER_ROUTE_TO_NODE.items()}
