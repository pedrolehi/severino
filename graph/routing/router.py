from graph.state import MultiAgentState
from agents.router_agent.models import Route, RouteDecision

ROUTER_ROUTE_TO_NODE = {
    Route.RAG: "rag_subgraph",
    Route.SERVICES: "service_caller_agent",
    Route.FALLBACK: "fallback_agent",
}


def route_from_decision(state: MultiAgentState) -> str:
    raw_decision = state.get("decision")
    if not raw_decision:
        return Route.FALLBACK.value

    route_value = raw_decision.get("route")
    if isinstance(route_value, dict):
        route_value = route_value.get("choice")
    if isinstance(route_value, str) and route_value in {r.value for r in Route}:
        return route_value

    try:
        return RouteDecision.model_validate(
            {
                "route": route_value,
                "confidence": raw_decision.get("confidence", 0.0),
            }
        ).route.value
    except Exception:
        return Route.FALLBACK.value


ROUTER_EDGES = {route.value: node for route, node in ROUTER_ROUTE_TO_NODE.items()}
