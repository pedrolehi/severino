"""Roteamento via OpenJEV (choice) + confidence para metricas."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agents.router_agent.models import (
    ROUTE_DESCRIPTIONS,
    ChoiceTrace,
    Route,
    RouteDecision,
    build_choice_trace,
)
from core.jev_client import call_systemone

_ROUTE_VALUES = {route.value for route in Route}


def _format_history(messages: list[BaseMessage], limit: int = 20) -> str:
    lines: list[str] = []
    for message in messages[-limit:]:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = message.__class__.__name__.lower()
        content = message.content
        text = content if isinstance(content, str) else str(content)
        lines.append(f"{role}: {text}")
    return "\n".join(lines) if lines else "(empty)"


def _last_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""


def build_router_state(
    *,
    messages: list[BaseMessage],
    capabilities_catalog: str,
) -> dict[str, Any]:
    return {
        "last_user_message": _last_user_text(messages).strip(),
        "conversation": _format_history(messages),
        "capabilities": capabilities_catalog.strip(),
        "routing_rules": (
            "Pick ONE route. Priority: "
            "(1) services — only if user wants to EXECUTE a transactional action "
            "covered by an item in `capabilities`; "
            "(2) rag — informative questions (how/what/policy/process/docs); "
            "(3) fallback — greetings, chit-chat, or out of scope. "
            "Missing capability for a topic is NOT fallback — prefer rag."
        ),
    }


def build_router_questions() -> dict[str, Any]:
    criteria = {
        route.value: description for route, description in ROUTE_DESCRIPTIONS.items()
    }
    return {
        "route": {
            "type": "choice",
            "instructions": (
                "Given `last_user_message`, `conversation`, `capabilities`, and "
                "`routing_rules`, pick the single best route."
            ),
            "criteria": criteria,
        },
    }


def _parse_route(raw: Any) -> Route:
    choice = ""
    if isinstance(raw, dict):
        choice = str(raw.get("choice") or "").strip().lower()
    if choice in _ROUTE_VALUES:
        return Route(choice)
    return Route.FALLBACK


def _parse_probabilities(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    probs = raw.get("probabilities")
    if not isinstance(probs, dict):
        return {}
    return {
        str(k): float(v)
        for k, v in probs.items()
        if isinstance(v, (int, float))
    }


def _parse_confidence(raw: Any, *, probabilities: dict[str, float]) -> float:
    if isinstance(raw, dict) and isinstance(raw.get("confidence"), (int, float)):
        return max(0.0, min(1.0, float(raw["confidence"])))
    if probabilities:
        return max(0.0, min(1.0, max(probabilities.values())))
    return 0.0


def _choice_trace_from_jev(route_block: Any, route: Route) -> ChoiceTrace:
    probs = _parse_probabilities(route_block)
    confidence = _parse_confidence(route_block, probabilities=probs)
    choice = route.value
    if isinstance(route_block, dict):
        raw_choice = str(route_block.get("choice") or "").strip().lower()
        if raw_choice in _ROUTE_VALUES:
            choice = raw_choice
    return build_choice_trace(
        choice=choice,
        confidence=confidence,
        probabilities=probs,
    )


def route_with_jev(
    *,
    messages: list[BaseMessage],
    capabilities_catalog: str,
) -> tuple[RouteDecision, ChoiceTrace]:
    """Chama OpenJEV; levanta JevClientError em falha."""
    state = build_router_state(
        messages=messages,
        capabilities_catalog=capabilities_catalog,
    )
    body = call_systemone(state=state, questions=build_router_questions())
    answers = body.get("answers") if isinstance(body.get("answers"), dict) else {}
    route_block = answers.get("route") if isinstance(answers, dict) else None

    route = _parse_route(route_block)
    trace = _choice_trace_from_jev(route_block, route)
    decision = RouteDecision(route=route, confidence=trace.confidence)
    return decision, trace
