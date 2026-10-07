from __future__ import annotations

from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from assistants.registry import get_assistant_by_id
from graph.sse_queue import push_sse
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


def fallback_agent(
    state: MultiAgentState, config: Optional[RunnableConfig] = None
) -> dict:
    from core.llm import llm

    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id não encontrado no estado")

    assistant = get_assistant_by_id(assistant_id)
    policy = resolve_rag_policy(assistant)

    fallback_source = state.get("fallback_source") or "router"
    fallback_reason = state.get("fallback_reason") or "router:fallback"
    fallback_hint = state.get("fallback_hint") or ""

    try:
        prompt_template = policy.fallback_prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(
            assistant_name=assistant.name,
            fallback_source=fallback_source,
            fallback_reason=fallback_reason,
            fallback_hint=fallback_hint,
            history=_format_history(state.get("messages") or []),
        )
    except Exception as exc:
        print(f"[Fallback Agent] Erro ao carregar/formatar prompt: {exc}")
        prompt = (
            f"Você é o assistente {assistant.name}. O sistema não conseguiu encontrar informações nos documentos internos. "
            f"Responda de forma breve e prestativa em português, admitindo que não encontrou a informação e sugerindo procurar o canal responsável."
        )

    last_human = ""
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            content = message.content
            last_human = content if isinstance(content, str) else str(content)
            break

    push_sse(config, {"event": "step", "id": "fallback", "status": "running"})

    configurable = (config or {}).get("configurable") or {}
    token_queue = configurable.get("token_queue")

    full_chunks: list[str] = []
    try:
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=last_human or "Olá"),
        ]
        if token_queue is not None:
            for chunk in llm.stream(messages):
                chunk_text = (
                    chunk.content
                    if isinstance(chunk.content, str)
                    else str(chunk.content)
                )
                if chunk_text:
                    full_chunks.append(chunk_text)
                    token_queue.put({"event": "token", "text": chunk_text})
            answer = "".join(full_chunks)
        else:
            response = llm.invoke(messages)
            content = response.content
            answer = content if isinstance(content, str) else str(content)
    except Exception as exc:
        print(f"[Fallback Agent] Erro no LLM: {exc}")
        answer = "Desculpe, não encontrei essa informação na documentação interna. Poderia reformular sua pergunta ou consultar o setor responsável?"
        if token_queue is not None and not full_chunks:
            token_queue.put({"event": "token", "text": answer})

    print(
        f"[Fallback Agent] source={fallback_source}, reason={fallback_reason}"
    )
    push_sse(config, {"event": "step", "id": "fallback", "status": "ok"})
    return {"messages": [AIMessage(content=answer)]}

