"""Runner multi-turno — segunda via de nota fiscal (GEF / SP)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from core.orchestrate_client import create_orchestrate_client
from flows.runtime import unexpected_input
from flows.segunda_via_nota_fiscal import domain as d
from graph.state import MultiAgentState

FLOW_NAME = "segunda_via_nota_fiscal"
SERVICE_LABEL = "o serviço de segunda via de nota fiscal"

STEP_ASK_SP = "ask_sp"
STEP_COLLECT = "collect_data"
STEP_COLLECT_MES = "collect_mes_ano"
STEP_ASK_NOVA_COMP = "ask_nova_competencia"
STEP_ASK_OUTRO_PREST = "ask_outro_prestador"
STEP_ASK_RETRY = "ask_retry"


def _done(message: str, flow_data: dict[str, Any] | None = None) -> dict:
    return {
        "active_flow": None,
        "flow_step": None,
        "flow_data": flow_data or {},
        "messages": [AIMessage(content=message)],
    }


def _continue(
    *,
    step: str,
    message: str,
    flow_data: dict[str, Any],
) -> dict:
    return {
        "active_flow": FLOW_NAME,
        "flow_step": step,
        "flow_data": flow_data,
        "messages": [AIMessage(content=message)],
    }


def _unexpected(resume_step: str, resume_prompt: str, flow_data: dict[str, Any]) -> dict:
    return unexpected_input(
        flow_name=FLOW_NAME,
        resume_step=resume_step,
        resume_prompt=resume_prompt,
        flow_data=flow_data,
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
        return d.ask_retry_message(competencia), False
    return (
        d.build_api_error_message(result.error_detail or "erro desconhecido")
        + "\n\n"
        + d.ask_retry_question(),
        False,
    )


def segunda_via_nota_fiscal_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = d.last_user_text(state.get("messages") or [])

    if step is None or step == STEP_ASK_SP:
        if step is None:
            return _continue(
                step=STEP_ASK_SP,
                message=d.ask_sp_message(),
                flow_data={},
            )

        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(STEP_ASK_SP, d.ask_sp_message(), flow_data)
        if not answer:
            return _done(d.fora_sp_message())

        return _continue(
            step=STEP_COLLECT,
            message=d.build_collect_prompt(),
            flow_data={},
        )

    if step == STEP_COLLECT:
        prompt = d.build_collect_prompt()
        if user_text.strip().lower() in {"cancelar", "cancel"}:
            return _unexpected(STEP_COLLECT, prompt, flow_data)

        slots = d.parse_coleta_text(user_text)
        if slots is None:
            return _unexpected(STEP_COLLECT, prompt, flow_data)

        err = d.validate_coleta(slots)
        if err:
            return _continue(
                step=STEP_COLLECT,
                message=d.build_collect_prompt(error=err),
                flow_data=flow_data,
            )

        flow_data.update(slots)
        flow_data["cnpj_senac_resolved"] = d.resolve_cnpj_senac(slots["cnpj_senac"])
        message, ok = _fetch_nf(flow_data)
        if ok:
            return _continue(
                step=STEP_ASK_NOVA_COMP,
                message=message + "\n\n" + d.ask_nova_competencia_message(),
                flow_data=flow_data,
            )
        return _continue(
            step=STEP_ASK_RETRY,
            message=message,
            flow_data=flow_data,
        )

    if step == STEP_COLLECT_MES:
        prompt = d.build_collect_mes_prompt()
        if user_text.strip().lower() in {"cancelar", "cancel"}:
            return _unexpected(STEP_COLLECT_MES, prompt, flow_data)

        mes_ano = user_text.strip()
        if not d.parse_mes_ano(mes_ano):
            return _unexpected(STEP_COLLECT_MES, prompt, flow_data)

        flow_data["mes_ano"] = mes_ano
        message, ok = _fetch_nf(flow_data)
        if ok:
            return _continue(
                step=STEP_ASK_NOVA_COMP,
                message=message + "\n\n" + d.ask_nova_competencia_message(),
                flow_data=flow_data,
            )
        return _continue(
            step=STEP_ASK_RETRY,
            message=message,
            flow_data=flow_data,
        )

    if step == STEP_ASK_NOVA_COMP:
        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(
                STEP_ASK_NOVA_COMP,
                d.ask_nova_competencia_message(),
                flow_data,
            )
        if answer:
            return _continue(
                step=STEP_COLLECT_MES,
                message=d.build_collect_mes_prompt(),
                flow_data=flow_data,
            )
        return _continue(
            step=STEP_ASK_OUTRO_PREST,
            message=d.ask_outro_prestador_message(),
            flow_data=flow_data,
        )

    if step == STEP_ASK_OUTRO_PREST:
        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(
                STEP_ASK_OUTRO_PREST,
                d.ask_outro_prestador_message(),
                flow_data,
            )
        if answer:
            return _continue(
                step=STEP_COLLECT,
                message=d.build_collect_prompt(),
                flow_data={},
            )
        return _done(d.something_else_message(), flow_data)

    if step == STEP_ASK_RETRY:
        answer = d.parse_boolean(user_text)
        if answer is None:
            return _unexpected(STEP_ASK_RETRY, d.ask_retry_question(), flow_data)
        if answer:
            return _continue(
                step=STEP_COLLECT,
                message=d.build_collect_prompt(),
                flow_data={},
            )
        return _done(d.something_else_message(), flow_data)

    return _done(d.something_else_message())
