"""Runner — abertura de chamado de carta convite GEP."""

from __future__ import annotations

from typing import Any

from flows.kit import (
    buttons_screen,
    field_text,
    form_data_of,
    last_user_text,
    match_choice,
    pack,
    reject,
    session_block,
)
from flows.payload import anexo_texto
from flows.runtime import parse_boolean
from flows.session import session_from_state
from flows.gep import common as c
from flows.gep.abertura_chamado_carta_convite import domain as d
from graph.state import MultiAgentState

STEP_TEMA = "tema"
STEP_SUBTEMA = "subtema"
STEP_DETALHE = "detalhe"
STEP_ANEXO = "ask_anexo"
STEP_ARQUIVO = "anexo"

FORM_DETALHE = c.detalhe_form(
    name="gep_carta_convite_detalhe",
    title="Carta Convite - Detalhes",
    field_title="Descreva sua solicitação de carta convite:",
    placeholder="Informe detalhadamente sua solicitação sobre carta convite...",
)

FORM_ARQUIVO = c.anexo_form(
    name="gep_carta_convite_anexo",
    title="Carta Convite - Anexo",
    field_title="Selecione o arquivo anexo:",
)


def gep_abertura_chamado_carta_convite_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)

    if step is None:
        missing = c.checar_sessao_gep(info)
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
            step=STEP_TEMA,
            flow_data={},
            screens=(buttons_screen("Qual assunto da carta convite?", d.TEMAS),),
        )

    if step == STEP_TEMA:
        tema_key = match_choice(user_text, d.TEMAS)
        if not tema_key:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_TEMA,
                prompt="Qual assunto da carta convite?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Qual assunto da carta convite?", d.TEMAS)],
            )
        flow_data["tema_key"] = tema_key
        tipo_label, classification = d.CLASSIFICATIONS[tema_key]
        flow_data["tipo"] = tipo_label
        flow_data["classification"] = classification

        if tema_key == "duvidas_gerais":
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_SUBTEMA,
                flow_data=flow_data,
                screens=(buttons_screen("Selecione o público da dúvida:", d.DUVIDAS_TEMAS),),
            )
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            texts=(f"Assunto: {tipo_label}",),
            screens=(FORM_DETALHE,),
        )

    if step == STEP_SUBTEMA:
        subtema = match_choice(user_text, d.DUVIDAS_TEMAS)
        if not subtema:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_SUBTEMA,
                prompt="Selecione o público da dúvida:",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Selecione o público da dúvida:", d.DUVIDAS_TEMAS)],
            )
        flow_data["subtema"] = subtema
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            texts=(f"Assunto: Dúvidas gerais ({subtema})",),
            screens=(FORM_DETALHE,),
        )

    if step == STEP_DETALHE:
        texto = field_text(user_text, "texto") or str(form_data_of(user_text).get("texto") or "").strip()
        if not texto:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_DETALHE,
                prompt="Por favor, detalhe a sua solicitação:",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[FORM_DETALHE],
            )
        flow_data["texto"] = texto
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_ANEXO,
            flow_data=flow_data,
            screens=(buttons_screen("Deseja enviar algum arquivo?", c.ASK_ANEXO),),
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
                resume_ui=[buttons_screen("Deseja enviar algum arquivo?", c.ASK_ANEXO)],
            )
        if answer:
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_ARQUIVO,
                flow_data=flow_data,
                screens=(FORM_ARQUIVO,),
            )
        message = c.submeter_chamado_gep(
            info,
            tipo=str(flow_data.get("tipo") or "Carta Convite"),
            classification=str(flow_data.get("classification") or "SNC_INT_003011"),
            texto=str(flow_data.get("texto") or ""),
            tema=str(flow_data.get("tipo") or "Carta Convite"),
            subtema=str(flow_data.get("subtema") or ""),
            anexo="",
        )
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
            prompt="Por favor, selecione o arquivo para envio:",
            flow_data=flow_data,
            service_label=d.SERVICE_LABEL,
            resume_ui=[FORM_ARQUIVO],
        )
    message = c.submeter_chamado_gep(
        info,
        tipo=str(flow_data.get("tipo") or "Carta Convite"),
        classification=str(flow_data.get("classification") or "SNC_INT_003011"),
        texto=str(flow_data.get("texto") or ""),
        tema=str(flow_data.get("tipo") or "Carta Convite"),
        subtema=str(flow_data.get("subtema") or ""),
        anexo=anexo,
    )
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )
