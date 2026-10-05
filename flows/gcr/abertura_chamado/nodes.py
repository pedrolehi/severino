"""Runner — abertura GCR. Devolve o protocolo que a API mandar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import (
    buttons_screen,
    field_text,
    form_data_of,
    last_user_text,
    pack,
    protocol_message,
    reject,
    render_named,
    session_block,
)
from flows.payload import anexo_texto, pessoa_body
from flows.runtime import parse_boolean
from flows.screen import load_screens, screen_text
from flows.session import missing_fields, session_from_state
from flows.gcr.abertura_chamado import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_DETALHE = "detalhe"
STEP_ANEXO = "ask_anexo"
STEP_ARQUIVO = "anexo"


def _abrir(info: dict[str, str], texto: str, anexo: str) -> str:
    body = pessoa_body(
        info,
        tipo=d.TIPO_CHAMADO,
        classification=d.CLASSIFICATION_ID,
        texto=texto,
        tema=d.TIPO_CHAMADO,
    )
    body["anexo"] = anexo
    result = create_orchestrate_client().post_json("/gcr/abertura-chamado", body)
    if result.ticket_id:
        return protocol_message(result.ticket_id, None)
    return protocol_message(None, result.error_detail)


def gcr_abertura_chamado_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)

    if step is None:
        missing = missing_fields(info, ("nome", "email", "cpf", "unidade"))
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
            step=STEP_DETALHE,
            flow_data={},
            screens=(SCREENS[STEP_DETALHE],),
        )

    if step == STEP_DETALHE:
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
        flow_data["texto"] = texto
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_ANEXO,
            flow_data=flow_data,
            screens=(buttons_screen("Deseja enviar algum arquivo?", d.ASK_ANEXO),),
        )

    if step == STEP_ANEXO:
        answer = parse_boolean(user_text)
        if answer is None:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_ANEXO,
                prompt="Deseja enviar algum arquivo?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Deseja enviar algum arquivo?", d.ASK_ANEXO)],
            )
        if answer:
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_ARQUIVO,
                flow_data=flow_data,
                screens=(SCREENS[STEP_ARQUIVO],),
            )
        message = _abrir(info, str(flow_data.get("texto") or ""), "")
        return pack(
            flow_name=d.FLOW_NAME,
            step=None,
            flow_data=flow_data,
            texts=(message,),
            done=True,
        )

    data = form_data_of(user_text)
    anexo = anexo_texto(data)
    if not anexo:
        return reject(
            flow_name=d.FLOW_NAME,
            resume_step=STEP_ARQUIVO,
            prompt=screen_text(SCREENS[STEP_ARQUIVO]),
            flow_data=flow_data,
            service_label=d.SERVICE_LABEL,
            resume_ui=[render_named(SCREENS, STEP_ARQUIVO)],
        )
    message = _abrir(info, str(flow_data.get("texto") or ""), anexo)
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )
