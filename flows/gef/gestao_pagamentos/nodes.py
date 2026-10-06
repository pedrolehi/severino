"""Runner — gestão de pagamentos GEF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import (
    buttons_screen,
    field_text,
    form_data_of,
    last_user_text,
    match_choice,
    pack,
    protocol_message,
    reject,
    render_named,
    session_block,
)
from flows.payload import anexo_texto, geral_body
from flows.runtime import parse_boolean
from flows.screen import load_screens, render_screen, screen_text
from flows.session import missing_fields, session_from_state
from flows.gef.gestao_pagamentos import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_TIPO = "tipo"
STEP_TEXTO = "texto"
STEP_DOC = "documento"
STEP_BANCO = "banco"
STEP_ANEXO = "anexo"
STEP_ARQUIVO = "arquivo"


def _resultado(result: Any) -> str:
    if result.ticket_id:
        return protocol_message(result.ticket_id, None)
    return protocol_message(None, result.error_detail)


def _texto_screen(tipo_key: str) -> dict[str, Any]:
    if tipo_key == "metodo":
        return SCREENS["texto_metodo"]
    return SCREENS["texto_problema"]


def _abrir(info: dict[str, str], flow_data: dict[str, Any], anexo: str) -> str:
    tipo_key = str(flow_data.get("tipo_key") or "")
    tipo_label = next(label for label, key in d.TIPOS if key == tipo_key)
    body: dict[str, Any] = geral_body(
        info,
        tipo=tipo_label,
        classification=d.classificacao_de(tipo_key),
        texto=str(flow_data.get("texto") or ""),
        area="gef",
    )
    body["DESCRIPTION"] = d.descricao_de(tipo_key)
    specs = d.ticket_specs(tipo_key, flow_data)
    body["TICKETSPECS"] = specs
    body["ticketSpecs"] = specs
    if anexo:
        body["anexo"] = {"file_url": anexo}
    result = create_orchestrate_client().post_json("/tools/abertura-chamado", body)
    return _resultado(result)


def _done(message: str, flow_data: dict[str, Any]) -> dict:
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )


def gef_gestao_pagamentos_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)
    tipo_key = str(flow_data.get("tipo_key") or "")

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
            step=STEP_TIPO,
            flow_data={},
            screens=(buttons_screen(d.ASK_TIPO, d.TIPOS),),
        )

    if step == STEP_TIPO:
        choice = match_choice(user_text, d.TIPOS)
        if not choice:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_TIPO,
                prompt=d.ASK_TIPO,
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_screen(buttons_screen(d.ASK_TIPO, d.TIPOS))],
            )
        flow_data["tipo_key"] = choice
        screen = _texto_screen(choice)
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_TEXTO,
            flow_data=flow_data,
            screens=(screen,),
        )

    if step == STEP_TEXTO:
        texto = field_text(user_text, "texto")
        screen = _texto_screen(tipo_key)
        if not texto:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_TEXTO,
                prompt=screen_text(screen),
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_screen(screen)],
            )
        flow_data["texto"] = texto
        if tipo_key == "metodo":
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_DOC,
                flow_data=flow_data,
                screens=(SCREENS[STEP_DOC],),
            )
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_ANEXO,
            flow_data=flow_data,
            screens=(buttons_screen(d.pergunta_anexo(tipo_key), d.SIM_NAO),),
        )

    if step == STEP_DOC:
        documento = field_text(user_text, "documento")
        if not documento:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_DOC,
                prompt=screen_text(SCREENS[STEP_DOC]),
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_named(SCREENS, STEP_DOC)],
            )
        flow_data["documento"] = documento
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_BANCO,
            flow_data=flow_data,
            screens=(SCREENS[STEP_BANCO],),
        )

    if step == STEP_BANCO:
        banco = field_text(user_text, "banco")
        if not banco:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_BANCO,
                prompt=screen_text(SCREENS[STEP_BANCO]),
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_named(SCREENS, STEP_BANCO)],
            )
        flow_data["banco"] = banco
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_ANEXO,
            flow_data=flow_data,
            screens=(buttons_screen(d.ASK_ANEXO_METODO, d.SIM_NAO),),
        )

    if step == STEP_ANEXO:
        answer = parse_boolean(user_text)
        if answer is None:
            choice = match_choice(user_text, d.SIM_NAO)
            if choice == "sim":
                answer = True
            elif choice == "nao":
                answer = False
        prompt = d.pergunta_anexo(tipo_key)
        if answer is None:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_ANEXO,
                prompt=prompt,
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_screen(buttons_screen(prompt, d.SIM_NAO))],
            )
        if answer:
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_ARQUIVO,
                flow_data=flow_data,
                screens=(SCREENS[STEP_ARQUIVO],),
            )
        return _done(_abrir(info, flow_data, ""), flow_data)

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
    return _done(_abrir(info, flow_data, anexo), flow_data)
