"""Runner — abertura de chamado de ponto eletrônico GEP."""

from __future__ import annotations

from typing import Any

from flows.kit import (
    buttons_screen,
    field_text,
    form_data_of,
    last_user_text,
    pack,
    question_screen,
    reject,
    session_block,
)
from flows.payload import anexo_texto
from flows.runtime import parse_boolean
from flows.session import session_from_state
from flows.gep import common as c
from flows.gep.abertura_chamado_ponto_eletronico import domain as d
from graph.state import MultiAgentState

STEP_DETALHE = "detalhe"
STEP_ANEXO = "ask_anexo"
STEP_ARQUIVO = "anexo"

PERGUNTA_DETALHE = question_screen(
    "Descreva o problema ocorrido no Ponto WEB: o erro ou o ajuste necessário."
)

FORM_ARQUIVO = c.anexo_form(
    name="gep_ponto_anexo",
    title="Ponto Eletrônico - Evidência / Anexo",
    field_title="Selecione o arquivo de comprovante ou print do erro:",
)


def gep_abertura_chamado_ponto_eletronico_node(state: MultiAgentState) -> dict:
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
            step=STEP_DETALHE,
            flow_data={},
            texts=(d.MSG_CONTEXTO,),
            screens=(PERGUNTA_DETALHE,),
        )

    if step == STEP_DETALHE:
        texto = field_text(user_text, "texto")
        if not texto:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_DETALHE,
                prompt="Por favor, detalhe o problema ocorrido no ponto eletrônico:",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[PERGUNTA_DETALHE],
            )
        flow_data["texto"] = texto
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_ANEXO,
            flow_data=flow_data,
            screens=(buttons_screen("Deseja enviar algum arquivo ou print?", c.ASK_ANEXO),),
        )

    if step == STEP_ANEXO:
        answer = parse_boolean(user_text)
        if answer is None:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_ANEXO,
                prompt="Deseja enviar algum arquivo ou print?",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[buttons_screen("Deseja enviar algum arquivo ou print?", c.ASK_ANEXO)],
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
            tipo=d.TIPO_CHAMADO,
            classification=d.CLASSIFICATION_ID,
            texto=str(flow_data.get("texto") or ""),
            tema=d.TIPO_CHAMADO,
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
        tipo=d.TIPO_CHAMADO,
        classification=d.CLASSIFICATION_ID,
        texto=str(flow_data.get("texto") or ""),
        tema=d.TIPO_CHAMADO,
        anexo=anexo,
    )
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )
