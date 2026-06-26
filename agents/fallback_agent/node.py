from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from assistants.registry import get_assistant_by_id
from graph.state import MultiAgentState
from rag.policy import resolve_rag_policy


def _format_history(messages: list[BaseMessage], limit: int = 6) -> str:
    lines: list[str] = []
    for message in messages[-limit:]:
        if isinstance(message, HumanMessage):
            role = "Usuário"
        elif isinstance(message, AIMessage):
            role = "Assistente"
        else:
            role = message.__class__.__name__
        content = message.content
        text = content if isinstance(content, str) else str(content)
        lines.append(f"{role}: {text}")
    return "\n".join(lines) if lines else "(sem histórico)"


def fallback_agent(state: MultiAgentState) -> dict:
    from core.llm import llm

    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id não encontrado no estado")

    assistant = get_assistant_by_id(assistant_id)
    policy = resolve_rag_policy(assistant)

    fallback_source = state.get("fallback_source") or "router"
    fallback_reason = state.get("fallback_reason")
    if not fallback_reason:
        decision = state.get("decision") or {}
        fallback_reason = decision.get("routing_reason") or "router:fallback"

    fallback_hint = state.get("fallback_hint") or ""
    prompt_template = policy.fallback_prompt_path.read_text(encoding="utf-8")
    prompt = prompt_template.format(
        assistant_name=assistant.name,
        fallback_source=fallback_source,
        fallback_reason=fallback_reason,
        fallback_hint=fallback_hint,
        history=_format_history(state.get("messages") or []),
    )

    last_human = ""
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            content = message.content
            last_human = content if isinstance(content, str) else str(content)
            break

    response = llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=last_human or "Olá"),
        ]
    )
    content = response.content
    answer = content if isinstance(content, str) else str(content)

    print(
        f"[Fallback Agent] source={fallback_source}, reason={fallback_reason}"
    )
    return {"messages": [AIMessage(content=answer)]}
