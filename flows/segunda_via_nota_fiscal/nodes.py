"""Runner multi-turno — segunda via de nota fiscal (GEF / SP)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from core.orchestrate_client import create_orchestrate_client
from flows.runtime import unexpected_input
from flows.screen import load_screens, render_screen, screen_text
from flows.segunda_via_nota_fiscal import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))

FLOW_NAME = "segunda_via_nota_fiscal"
SERVICE_LABEL = "o serviço de segunda via de nota fiscal"

STEP_ASK_SP = "ask_sp"
STEP_COLLECT = "collect_data"
STEP_COLLECT_MES = "collect_mes_ano"
STEP_ASK_NOVA_COMP = "ask_nova_competencia"
STEP_ASK_OUTRO_PREST = "ask_outro_prestador"
STEP_ASK_RETRY = "ask_retry"


def _ai(content: str, ui: list[dict[str, Any]] | None = None) -> AIMessage:
    if not ui:
        return AIMessage(content=content)
    return AIMessage(content=content, additional_kwargs={"ui": ui})


def _screen_block(name: str) -> dict[str, Any]:
    return render_screen(SCREENS[name])


def _screen_text(name: str) -> str:
    return screen_text(SCREENS[name])


def _ui_for(*, texts: tuple[str, ...] = (), screens: tuple[str, ...] = ()) -> tuple[str, list[dict[str, Any]]]:
    ui: list[dict[str, Any]] = []
    parts: list[str] = []
    for text in texts:
        cleaned = text.strip()
        if not cleaned:
            continue
        ui.append({"response_type": "text", "text": cleaned})
        parts.append(cleaned)
    for name in screens:
        ui.append(_screen_block(name))
        parts.append(_screen_text(name))
    return "\n\n".join(parts), ui


def _done(
    message: str,
    flow_data: dict[str, Any] | None = None,
    ui: list[dict[str, Any]] | None = None,
) -> dict:
    return {
        "active_flow": None,
        "flow_step": None,
        "flow_data": flow_data or {},
        "messages": [_ai(message, ui)],
    }


def _continue(
    *,
    step: str,
    message: str,
    flow_data: dict[str, Any],
    ui: list[dict[str, Any]] | None = None,
) -> dict:
    return {
        "active_flow": FLOW_NAME,
        "flow_step": step,
        "flow_data": flow_data,
        "messages": [_ai(message, ui)],
    }


def _show(
    *,
    step: str,
    flow_data: dict[str, Any],
    texts: tuple[str, ...] = (),
    screens: tuple[str, ...] = (),
    done: bool = False,
) -> dict:
    message, ui = _ui_for(texts=texts, screens=screens)
    if done:
        return _done(message, flow_data, ui or None)
    return _continue(step=step, message=message, flow_data=flow_data, ui=ui or None)


def _unexpected(resume_step: str, screen_name: str, flow_data: dict[str, Any]) -> dict:
    data = dict(flow_data)
    data["_resume_ui"] = [_screen_block(screen_name)]
    return unexpected_input(
        flow_name=FLOW_NAME,
        resume_step=resume_step,
        resume_prompt=_screen_text(screen_name),
        flow_data=data,
        service_label=SERVICE_LABEL,
    )


def _fetch_nf(flow_data: dict[str, Any]) -> tuple[str, bool]:
    """Retorna (mensagem, sucesso)."""
    parsed = d.parse_mes_ano(str(flow_data.get("mes_ano") or ""))
    if not parsed:
        return d.build_api_error_message("Competência inválida."), False

    ano, mes = parsed
    cnpj_senac = d.resolve_cnpj_senac(str(flow_data.get("cnpj_senac") or "")) or ""
    cnpj_cliente = str(flow_data.get("cnpj_cliente") or "")

    client = create_orchestrate_client()
    result = client.get_nota_fiscal(
        ano=ano,
        mes=mes,
        cnpj_senac=cnpj_senac,
        cnpj_cliente=cnpj_cliente,
    )

    competencia = d.to_mes_ano_exibicao(str(flow_data.get("mes_ano") or ""))
    if result.ok:
        return d.build_success_message(result.links), True
    if result.not_found:
        return d.build_not_found_message(competencia), False
    return d.build_api_error_message(result.error_detail or "erro desconhecido"), False


def segunda_via_nota_fiscal_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = d.last_user_text(state.get("messages") or [])

    if step is None or step == STEP_ASK_SP:
        if step is None:
            return _show(step=STEP_ASK_SP, flow_data={}, screens=(STEP_ASK_SP,))

        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(STEP_ASK_SP, STEP_ASK_SP, flow_data)
        if not answer:
            return _done(d.fora_sp_message())

        return _show(step=STEP_COLLECT, flow_data={}, screens=("collect",))

    if step == STEP_COLLECT:
        if user_text.strip().lower() in {"cancelar", "cancel"} or d.is_form_cancel(user_text):
            return _unexpected(STEP_COLLECT, "collect", flow_data)

        slots = d.parse_coleta_text(user_text)
        if slots is None:
            return _unexpected(STEP_COLLECT, "collect", flow_data)

        err = d.validate_coleta(slots)
        if err:
            return _show(
                step=STEP_COLLECT,
                flow_data=flow_data,
                texts=(err,),
                screens=("collect",),
            )

        flow_data.update(slots)
        flow_data["cnpj_senac_resolved"] = d.resolve_cnpj_senac(slots["cnpj_senac"])
        message, ok = _fetch_nf(flow_data)
        if ok:
            return _show(
                step=STEP_ASK_NOVA_COMP,
                flow_data=flow_data,
                texts=(message,),
                screens=(STEP_ASK_NOVA_COMP,),
            )
        return _show(
            step=STEP_ASK_RETRY,
            flow_data=flow_data,
            texts=(message,),
            screens=(STEP_ASK_RETRY,),
        )

    if step == STEP_COLLECT_MES:
        if user_text.strip().lower() in {"cancelar", "cancel"} or d.is_form_cancel(user_text):
            return _unexpected(STEP_COLLECT_MES, "collect_mes", flow_data)

        mes_ano = d.parse_mes_ano_input(user_text)
        if not mes_ano:
            return _unexpected(STEP_COLLECT_MES, "collect_mes", flow_data)

        flow_data["mes_ano"] = mes_ano
        message, ok = _fetch_nf(flow_data)
        if ok:
            return _show(
                step=STEP_ASK_NOVA_COMP,
                flow_data=flow_data,
                texts=(message,),
                screens=(STEP_ASK_NOVA_COMP,),
            )
        return _show(
            step=STEP_ASK_RETRY,
            flow_data=flow_data,
            texts=(message,),
            screens=(STEP_ASK_RETRY,),
        )

    if step == STEP_ASK_NOVA_COMP:
        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(STEP_ASK_NOVA_COMP, STEP_ASK_NOVA_COMP, flow_data)
        if answer:
            return _show(
                step=STEP_COLLECT_MES,
                flow_data=flow_data,
                screens=("collect_mes",),
            )
        return _show(
            step=STEP_ASK_OUTRO_PREST,
            flow_data=flow_data,
            screens=(STEP_ASK_OUTRO_PREST,),
        )

    if step == STEP_ASK_OUTRO_PREST:
        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(STEP_ASK_OUTRO_PREST, STEP_ASK_OUTRO_PREST, flow_data)
        if answer:
            return _show(step=STEP_COLLECT, flow_data={}, screens=("collect",))
        return _done(d.something_else_message(), flow_data)

    if step == STEP_ASK_RETRY:
        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(STEP_ASK_RETRY, STEP_ASK_RETRY, flow_data)
        if answer:
            return _show(step=STEP_COLLECT, flow_data={}, screens=("collect",))
        return _done(d.something_else_message(), flow_data)

    return _done(d.something_else_message())
