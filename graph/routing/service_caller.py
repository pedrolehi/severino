from graph.state import MultiAgentState
from flows.registry import FLOW_BUILDERS
from langgraph.graph import END


def build_service_caller_edges() -> dict:
    edges = {"tools": "tools_node", "end": END}
    for name in FLOW_BUILDERS:
        edges[name] = name
    return edges


def route_from_service_caller(state: MultiAgentState):
    last_message = state["messages"][-1]

    # Se a última mensagem contiver chamadas de ferramentas, roteia para o nó de ferramentas
    if getattr(last_message, "tool_calls", None):
        return "tools"

    # Se houver um serviço alvo definido, roteia para o nó do serviço alvo
    target = state.get("service_target")
    if target and target in FLOW_BUILDERS:
        return target

    return "end"
