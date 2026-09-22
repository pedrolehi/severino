"""Monta payload `conversation` para POST /rag/answer (search-vectory)."""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Alinha com DEFAULT_CONVERSATION_TURNS do search-vectory.
DEFAULT_MAX_TURNS = 6
DEFAULT_MAX_CONTENT_CHARS = 1200


def _message_text(message: BaseMessage) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    if content is None:
        return ""
    return str(content).strip()


def _clip(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def build_conversation_from_messages(
    messages: Sequence[BaseMessage] | None,
    *,
    exclude_trailing_user: bool = True,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
) -> list[dict[str, str]]:
    """Converte historico LangChain → turns `{role, content}` da API vectory.

    A pergunta atual fica em `query`; por default o ultimo HumanMessage
    nao entra no historico (evita duplicar PERGUNTA_ATUAL).
    """
    if not messages:
        return []

    items = list(messages)
    if (
        exclude_trailing_user
        and items
        and isinstance(items[-1], HumanMessage)
    ):
        items = items[:-1]

    turns: list[dict[str, str]] = []
    for message in items:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue
        text = _clip(_message_text(message), max_content_chars)
        if not text:
            continue
        turns.append({"role": role, "content": text})

    if max_turns > 0 and len(turns) > max_turns:
        turns = turns[-max_turns:]
    return turns


def conversation_turn_count(conversation: Sequence[dict[str, Any]] | None) -> int:
    return len(conversation or [])
