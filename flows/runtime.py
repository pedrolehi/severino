"""Runtime nativo de flows — confirm exit e signals de controle."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage

from flows.screen import render_screen

STEP_CONFIRM_EXIT = "__confirm_exit__"
FLOW_CONTROL_UNEXPECTED = "unexpected_input"

_RESUME_STEP_KEY = "_resume_step"
_RESUME_PROMPT_KEY = "_resume_prompt"
_RESUME_UI_KEY = "_resume_ui"
_RESUME_KEYS = {
    _RESUME_STEP_KEY,
    _RESUME_PROMPT_KEY,
    _RESUME_UI_KEY,
    "_service_label",
}


def parse_boolean(text: str) -> bool | None:
    normalized = (text or "").strip().lower()
    if normalized in {"sim", "s", "true", "yes", "1"}:
        return True
    if normalized in {"não", "nao", "n", "false", "no", "0"}:
        return False
    return None


def confirm_exit_message(*, service_label: str | None = None) -> str:
    label = service_label or "este serviço"
    return (
        "Não entendi sua resposta.\n\n"
        f"Deseja realmente sair de {label}?"
    )


def stay_in_service_prefix() -> str:
    return "Ok, vamos continuar.\n\n"


def left_service_message() -> str:
    return "Precisa de ajuda em algo mais?"


def _yes_no_ui(text: str) -> list[dict[str, Any]]:
    return [
        render_screen(
            {
                "component": "buttons",
                "text": text,
                "buttons": [
                    {"label": "Sim", "value": "sim"},
                    {"label": "Não", "value": "nao"},
                ],
            }
        )
    ]


def _ai(content: str, ui: list[dict[str, Any]] | None = None) -> AIMessage:
    if not ui:
        return AIMessage(content=content)
    return AIMessage(content=content, additional_kwargs={"ui": ui})


def unexpected_input(
    *,
    flow_name: str,
    resume_step: str,
    resume_prompt: str,
    flow_data: dict[str, Any] | None = None,
    service_label: str | None = None,
) -> dict[str, Any]:
    """Sinal: input fora do esperado. O wrapper nativo vira confirm-exit."""
    data = dict(flow_data or {})
    data[_RESUME_STEP_KEY] = resume_step
    data[_RESUME_PROMPT_KEY] = resume_prompt
    if service_label:
        data["_service_label"] = service_label
    return {
        "flow_control": FLOW_CONTROL_UNEXPECTED,
        "active_flow": flow_name,
        "flow_step": resume_step,
        "flow_data": data,
        "messages": [],
    }


def _handle_confirm_exit(state: dict[str, Any]) -> dict[str, Any]:
    user_text = _last_user_text(state.get("messages") or [])
    flow_data = dict(state.get("flow_data") or {})
    active_flow = state.get("active_flow")
    service_label = flow_data.get("_service_label")

    answer = parse_boolean(user_text)
    if answer is None:
        prompt = confirm_exit_message(
            service_label=str(service_label) if service_label else None
        )
        return {
            "active_flow": active_flow,
            "flow_step": STEP_CONFIRM_EXIT,
            "flow_data": flow_data,
            "messages": [_ai(prompt, _yes_no_ui(prompt))],
        }

    if answer:
        return {
            "active_flow": None,
            "flow_step": None,
            "flow_data": {},
            "service_target": None,
            "messages": [AIMessage(content=left_service_message())],
        }

    resume_step = str(flow_data.get(_RESUME_STEP_KEY) or "")
    resume_prompt = str(flow_data.get(_RESUME_PROMPT_KEY) or "")
    resume_ui = flow_data.get(_RESUME_UI_KEY)
    resume_data = {
        k: v for k, v in flow_data.items() if k not in _RESUME_KEYS
    }
    prefix = stay_in_service_prefix().strip()
    ui: list[dict[str, Any]] = [{"response_type": "text", "text": prefix}]
    if isinstance(resume_ui, list) and resume_ui:
        ui.extend(item for item in resume_ui if isinstance(item, dict))
    else:
        ui.extend(_yes_no_ui(resume_prompt) if resume_prompt else [])
    return {
        "active_flow": active_flow,
        "flow_step": resume_step or None,
        "flow_data": resume_data,
        "messages": [_ai(prefix + "\n\n" + resume_prompt, ui)],
    }


def _last_user_text(messages: list[Any]) -> str:
    from langchain_core.messages import HumanMessage

    for message in reversed(messages or []):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""


def _to_confirm_exit(result: dict[str, Any]) -> dict[str, Any]:
    flow_data = dict(result.get("flow_data") or {})
    service_label = flow_data.get("_service_label")
    cleaned = {
        k: v
        for k, v in result.items()
        if k != "flow_control"
    }
    cleaned["flow_step"] = STEP_CONFIRM_EXIT
    cleaned["flow_data"] = flow_data
    prompt = confirm_exit_message(
        service_label=str(service_label) if service_label else None
    )
    cleaned["messages"] = [_ai(prompt, _yes_no_ui(prompt))]
    return cleaned


def wrap_flow_node(node: Callable[..., dict]) -> Callable[..., dict]:
    """Envelope nativo: trata __confirm_exit__ e flow_control=unexpected_input."""

    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("flow_step") == STEP_CONFIRM_EXIT:
            return _handle_confirm_exit(state)

        result = node(state)
        if not isinstance(result, dict):
            return result

        if result.get("flow_control") == FLOW_CONTROL_UNEXPECTED:
            return _to_confirm_exit(result)

        if "flow_control" in result:
            result = {k: v for k, v in result.items() if k != "flow_control"}
        return result

    return wrapped
