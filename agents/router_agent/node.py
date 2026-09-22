from pathlib import Path

from langchain_core.messages import SystemMessage

from agents.router_agent.jev_router import route_with_jev
from agents.router_agent.models import (
    Route,
    RouteDecision,
    decision_to_payload,
    get_route_catalog,
)
from assistants.capabilities import resolve_capabilities
from core.config import USE_JEV_ROUTER
from core.jev_client import JevClientError
from core.llm import llm
from graph.state import MultiAgentState

PROMPT_PATH = Path(__file__).parent / "prompts" / "router_prompt.txt"

# Re-export para imports legados (graph.routing.router, etc.)
__all__ = ["Route", "RouteDecision", "router_agent"]


def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


structured_llm = llm.with_structured_output(RouteDecision)


def _route_with_llm(state: MultiAgentState) -> RouteDecision:
    caps = resolve_capabilities(state["assistant_id"])
    system_prompt = load_prompt().format(
        routes=get_route_catalog(), capabilities=caps.router_catalog()
    )
    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history
    return structured_llm.invoke(messages)


def router_agent(state: MultiAgentState) -> dict:
    print("[ROUTER AGENT] Iniciando agente de roteamento...")
    assistant_id = state["assistant_id"]
    if not assistant_id:
        raise ValueError("Assistant ID não encontrado no estado")

    decision: RouteDecision
    source = "llm"
    choice_trace = None

    if USE_JEV_ROUTER:
        try:
            caps = resolve_capabilities(assistant_id)
            decision, choice_trace = route_with_jev(
                messages=state["messages"][-20:],
                capabilities_catalog=caps.router_catalog(),
            )
            source = "jev"
        except JevClientError as exc:
            print(f"[ROUTER AGENT] JEV falhou ({exc}); fallback LLM")
            decision = _route_with_llm(state)
            source = "llm_fallback"
    else:
        decision = _route_with_llm(state)

    payload = decision_to_payload(
        decision, source=source, choice_trace=choice_trace
    )
    print(
        f"[ROUTER AGENT] source={source}, route={payload['route']}, "
        f"confidence={payload['confidence']:.3f}, "
        f"trace={payload['trace']}"
    )

    return {"decision": payload}
