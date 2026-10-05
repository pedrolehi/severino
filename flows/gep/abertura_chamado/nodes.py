"""Runner — abertura GEP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import (
    buttons_screen,
    form_data_of,
    last_user_text,
    match_choice,
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
from flows.gep.abertura_chamado import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_ASSUNTO = "assunto"
STEP_CARTA = "carta"
STEP_DETALHE = "detalhe"
STEP_ANEXO = "ask_anexo"
STEP_ARQUIVO = "anexo"


def _abrir(info: dict[str, str], flow_data: dict[str, Any], anexo: str) -> str:
    tipo, classification = d.TIPOS[str(flow_data["tipo_key"])]
    body = pessoa_body(
        info,
        tipo=tipo,
        classification=classification,
        texto=str(flow_data.get("texto") or ""),
        tema=str(flow_data.get("tema") or tipo),
    )
    body["anexo"] = anexo
    result = create_orchestrate_client().post_json("/gep/abertura-chamado", body)
    if result.ticket_id:
        return protocol_message(result.ticket_id, None)
    return protocol_message(None, result.error_detail)


def gep_abertura_chamado_node(state: MultiAgentState) -> dict:
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
            step=STEP_ASSUNTO,
            flow_data={},
            screens=(buttons_screen("Qual assunto do chamado GEP?", d.ASSUNTOS),),
        )

    if step == STEP_ASSUNTO:
        choice = match_choice(user_text, d.ASSUNTOS)
        if not choice:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_ASSUNTO,
                prompt="Qual assunto do chamado GEP?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Qual assunto do chamado GEP?", d.ASSUNTOS)],
            )
        if choice == "carta":
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_CARTA,
                flow_data=flow_data,
                screens=(buttons_screen("Qual tema da carta convite?", d.CARTA),),
            )
        flow_data["tipo_key"] = choice
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            screens=(SCREENS[STEP_DETALHE],),
        )

    if step == STEP_CARTA:
        choice = match_choice(user_text, d.CARTA)
        if not choice:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_CARTA,
                prompt="Qual tema da carta convite?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Qual tema da carta convite?", d.CARTA)],
            )
        flow_data["tipo_key"] = choice
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            screens=(SCREENS[STEP_DETALHE],),
        )

    if step == STEP_DETALHE:
        data = form_data_of(user_text)
        texto = str(data.get("texto") or "").strip()
        tema = str(data.get("tema") or "").strip()
        if not texto or (flow_data.get("tipo_key") == "beneficios" and not tema):
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_DETALHE,
                prompt=screen_text(SCREENS[STEP_DETALHE]),
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_named(SCREENS, STEP_DETALHE)],
            )
        flow_data["texto"] = texto
        flow_data["tema"] = tema
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
        message = _abrir(info, flow_data, "")
        return pack(
            flow_name=d.FLOW_NAME,
            step=None,
            flow_data=flow_data,
            texts=(message,),
            done=True,
        )

    anexo = anexo_texto(form_data_of(user_text))
    if not anexo:
        return reject(
            flow_name=d.FLOW_NAME,
            resume_step=STEP_ARQUIVO,
            prompt=screen_text(SCREENS[STEP_ARQUIVO]),
            flow_data=flow_data,
            service_label=d.SERVICE_LABEL,
            resume_ui=[render_named(SCREENS, STEP_ARQUIVO)],
        )
    message = _abrir(info, flow_data, anexo)
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )
