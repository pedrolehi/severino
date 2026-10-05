"""Atalhos de tela e de input usados pelos flows portados."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from flows.runtime import unexpected_input
from flows.screen import render_screen, screen_text


def last_user_text(messages: list[Any]) -> str:
    for message in reversed(messages or []):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""


def parse_form_body(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw.startswith("{"):
        return None
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("form_data"), dict):
        return None
    return body


def form_data_of(text: str) -> dict[str, Any]:
    body = parse_form_body(text)
    if body is None:
        return {}
    data = body.get("form_data")
    return data if isinstance(data, dict) else {}


def is_form_cancel(text: str) -> bool:
    body = parse_form_body(text)
    return bool(body and body.get("form_operation") == "cancel")


def field_text(text: str, key: str) -> str | None:
    if is_form_cancel(text):
        return None
    data = form_data_of(text)
    if data:
        value = data.get(key)
        cleaned = str(value).strip() if value is not None else ""
        return cleaned or None
    raw = (text or "").strip()
    if not raw or raw.startswith("{"):
        return None
    return raw


def match_choice(text: str, choices: list[tuple[str, str]]) -> str | None:
    raw = (text or "").strip().casefold()
    if not raw or is_form_cancel(text):
        return None
    data = form_data_of(text)
    candidates = [raw]
    for value in data.values():
        if value is not None:
            candidates.append(str(value).strip().casefold())
    for label, value in choices:
        keys = {label.strip().casefold(), value.strip().casefold()}
        if any(item in keys for item in candidates):
            return value
    return None


def buttons_screen(text: str, choices: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "component": "buttons",
        "text": text,
        "buttons": [{"label": label, "value": value} for label, value in choices],
    }


def select_form(
    *,
    title: str,
    name: str,
    key: str,
    field_title: str,
    options: list[tuple[str, str]],
    help_text: str = "",
) -> dict[str, Any]:
    return {
        "component": "form",
        "title": title,
        "name": name,
        "fields": [
            {
                "key": key,
                "title": field_title,
                "widget": "select",
                "help": help_text,
                "required": True,
                "options": [{"label": label, "value": value} for label, value in options],
            }
        ],
    }


def ai_message(content: str, ui: list[dict[str, Any]] | None = None) -> AIMessage:
    if not ui:
        return AIMessage(content=content)
    return AIMessage(content=content, additional_kwargs={"ui": ui})


def render_named(screens: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    return render_screen(screens[name])


def pack(
    *,
    flow_name: str,
    step: str | None,
    flow_data: dict[str, Any],
    texts: tuple[str, ...] = (),
    screens: tuple[dict[str, Any], ...] = (),
    done: bool = False,
) -> dict[str, Any]:
    ui: list[dict[str, Any]] = []
    parts: list[str] = []
    for text in texts:
        cleaned = text.strip()
        if not cleaned:
            continue
        ui.append({"response_type": "text", "text": cleaned})
        parts.append(cleaned)
    for screen in screens:
        ui.append(render_screen(screen))
        parts.append(screen_text(screen))
    message = "\n\n".join(parts)
    payload: dict[str, Any] = {
        "active_flow": None if done else flow_name,
        "flow_step": None if done else step,
        "flow_data": flow_data,
        "messages": [ai_message(message, ui or None)],
    }
    if done:
        payload["service_target"] = None
    return payload


def reject(
    *,
    flow_name: str,
    resume_step: str,
    prompt: str,
    flow_data: dict[str, Any],
    service_label: str,
    resume_ui: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    data = dict(flow_data)
    if resume_ui:
        data["_resume_ui"] = resume_ui
    return unexpected_input(
        flow_name=flow_name,
        resume_step=resume_step,
        resume_prompt=prompt,
        flow_data=data,
        service_label=service_label,
    )


def session_block(missing: list[str]) -> str:
    joined = ", ".join(missing)
    return (
        "Não consigo seguir este serviço. "
        f"A sessão não traz {joined} do colaborador."
    )


def protocol_message(ticket_id: str | None, error: str | None) -> str:
    if ticket_id:
        return f"Chamado aberto. Protocolo: {ticket_id}."
    detail = (error or "a integração não devolveu protocolo").strip()
    return f"Não abri o chamado. {detail}"
