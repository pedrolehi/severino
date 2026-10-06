"""Runner — gestão de pagamentos GEF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import (
    buttons_screen,
    field_text,
    last_user_text,
    match_choice,
    pack,
    protocol_message,
    reject,
    render_named,
    session_block,
)
from flows.payload import geral_body
from flows.screen import load_screens, screen_text
from flows.session import missing_fields, session_from_state
from flows.gef.gestao_pagamentos import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_GESTAO = "gestao"
STEP_TEXTO = "texto"


def _resultado(result) -> str:
    if result.ticket_id:
        return protocol_message(result.ticket_id, None)
    return protocol_message(None, result.error_detail)


def gef_gestao_pagamentos_node(state: MultiAgentState) -> dict:
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
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_GESTAO,
            flow_data={},
            screens=(buttons_screen("Qual tipo de pagamento?", d.GESTAO),),
        )

    if step == STEP_GESTAO:
        choice = match_choice(user_text, d.GESTAO)
        picked = next((item for item in d.GESTAO if item[1] == choice), None)
        if picked is None:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_GESTAO,
                prompt="Qual tipo de pagamento?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Qual tipo de pagamento?", d.GESTAO)],
            )
        flow_data["tipo"] = picked[0]
        flow_data["classification"] = picked[1]
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_TEXTO,
            flow_data=flow_data,
            screens=(SCREENS[STEP_TEXTO],),
        )

    texto = field_text(user_text, "texto")
    if not texto:
        return reject(
            flow_name=d.FLOW_NAME,
            resume_step=STEP_TEXTO,
            prompt=screen_text(SCREENS[STEP_TEXTO]),
            flow_data=flow_data,
            service_label=d.SERVICE_LABEL,
            resume_ui=[render_named(SCREENS, STEP_TEXTO)],
        )
    body = geral_body(
        info,
        tipo=str(flow_data.get("tipo") or ""),
        classification=str(flow_data.get("classification") or ""),
        texto=texto,
        area="gef",
    )
    result = create_orchestrate_client().post_json("/geral/abertura-chamado", body)
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(_resultado(result),),
        done=True,
    )
