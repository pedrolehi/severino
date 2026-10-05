"""Runner — abertura GEDUC. Assunto da frase, protocolo só se a API devolver."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import (
    field_text,
    last_user_text,
    match_choice,
    pack,
    protocol_message,
    reject,
    render_named,
    select_form,
    session_block,
)
from flows.payload import geral_body
from flows.screen import load_screens, screen_text
from flows.session import missing_fields, session_from_state
from flows.geduc.abertura_chamado import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_ASSUNTO = "assunto"
STEP_DETALHE = "detalhe"


def geduc_abertura_chamado_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)

    if step is None:
        missing = missing_fields(info, ("nome", "email"))
        if missing:
            return pack(
                flow_name=d.FLOW_NAME,
                step=None,
                flow_data={},
                texts=(session_block(missing),),
                done=True,
            )
        subject = d.match_subject(user_text)
        if subject:
            flow_data["assunto"] = subject
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_DETALHE,
                flow_data=flow_data,
                texts=(f"Assunto: {subject}",),
                screens=(SCREENS[STEP_DETALHE],),
            )
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_ASSUNTO,
            flow_data={},
            screens=(
                select_form(
                    title="Abertura de chamado GEDUC",
                    name="geduc_abertura_chamado_assunto",
                    key="assunto",
                    field_title="Assunto",
                    options=d.subject_choices(),
                ),
            ),
        )

    if step == STEP_ASSUNTO:
        choice = match_choice(user_text, d.subject_choices()) or d.match_subject(user_text)
        if not choice:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_ASSUNTO,
                prompt="Qual assunto do chamado GEDUC?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[
                    select_form(
                        title="Abertura de chamado GEDUC",
                        name="geduc_abertura_chamado_assunto",
                        key="assunto",
                        field_title="Assunto",
                        options=d.subject_choices(),
                    )
                ],
            )
        flow_data["assunto"] = choice
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            texts=(f"Assunto: {choice}",),
            screens=(SCREENS[STEP_DETALHE],),
        )

    texto = field_text(user_text, "texto")
    if not texto:
        return reject(
            flow_name=d.FLOW_NAME,
            resume_step=STEP_DETALHE,
            prompt=screen_text(SCREENS[STEP_DETALHE]),
            flow_data=flow_data,
            service_label=d.SERVICE_LABEL,
            resume_ui=[render_named(SCREENS, STEP_DETALHE)],
        )
    assunto = str(flow_data.get("assunto") or "")
    body = geral_body(info, tipo=assunto, classification="", texto=texto)
    result = create_orchestrate_client().post_json("/geral/abertura-chamado", body)
    if result.ticket_id:
        message = protocol_message(result.ticket_id, None)
    else:
        message = protocol_message(None, result.error_detail)
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )
