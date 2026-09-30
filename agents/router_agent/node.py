import time
from pathlib import Path

from typing import Optional

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

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
from graph.sse_queue import push_sse
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


def router_agent(
    state: MultiAgentState, config: Optional[RunnableConfig] = None
) -> dict:
    t_router = time.perf_counter()
    metadata = (config or {}).get("metadata") or {}
    invoke_t0 = metadata.get("invoke_t0")
    if isinstance(invoke_t0, (int, float)):
        pre_ms = int((t_router - invoke_t0) * 1000)
        print(
            f"[ROUTER AGENT] invoke_to_router_ms={pre_ms}",
            flush=True,
        )
    print("[ROUTER AGENT] Iniciando agente de roteamento...", flush=True)
    push_sse(config, {"event": "step", "id": "router", "status": "running"})
    assistant_id = state["assistant_id"]
    if not assistant_id:
        raise ValueError("Assistant ID não encontrado no estado")

    decision: RouteDecision
    source = "llm"
    choice_trace = None

    jev_ms: int | None = None
    caps_ms: int | None = None
    if USE_JEV_ROUTER:
        try:
            t_caps = time.perf_counter()
            caps = resolve_capabilities(assistant_id)
            caps_ms = int((time.perf_counter() - t_caps) * 1000)
            catalog = caps.router_catalog()
            t0 = time.perf_counter()
            decision, choice_trace = route_with_jev(
                messages=state["messages"][-20:],
                capabilities_catalog=catalog,
            )
            jev_ms = int((time.perf_counter() - t0) * 1000)
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
    router_ms = int((time.perf_counter() - t_router) * 1000)
    timing = ""
    if caps_ms is not None:
        timing += f", caps_ms={caps_ms}"
    if jev_ms is not None:
        timing += f", jev_ms={jev_ms}"
    print(
        f"[ROUTER AGENT] source={source}, route={payload['route']}, "
        f"confidence={payload['confidence']:.3f}, router_ms={router_ms}{timing}, "
        f"trace={payload['trace']}",
        flush=True,
    )
    push_sse(
        config,
        {
            "event": "step",
            "id": "router",
            "status": "ok",
            "route": payload["route"],
        },
    )

    return {"decision": payload}
