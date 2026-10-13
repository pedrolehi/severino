"""Runner — abertura GEDUC. Roteamento completo por assunto e subtema, com anexo e protocolo."""

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
    select_form,
    session_block,
)
from flows.payload import anexo_texto, geral_body
from flows.runtime import parse_boolean
from flows.screen import load_screens, screen_text
from flows.session import missing_fields, session_from_state
from flows.geduc.abertura_chamado import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_ASSUNTO = "assunto"
STEP_SUBTEMA = "subtema"
STEP_DETALHE = "detalhe"
STEP_ANEXO = "ask_anexo"
STEP_ARQUIVO = "anexo"


def _submeter(info: dict[str, str], flow_data: dict[str, Any], anexo: str) -> str:
    assunto = str(flow_data.get("assunto") or "Abertura GEDUC")
    subtema = str(flow_data.get("subtema") or "")
    texto = str(flow_data.get("texto") or "")
    texto_completo = f"[{subtema}] {texto}" if subtema else texto

    body = geral_body(
        info,
        tipo=assunto,
        classification="GEDUC",
        texto=texto_completo,
        area="geduc",
    )
    if anexo:
        body["anexo"] = anexo

    result = create_orchestrate_client().open_ticket(body)
    if result.ticket_id:
        return protocol_message(result.ticket_id, None)
    return protocol_message(None, result.error_detail)


def _subtema_screen(assunto: str, options: list[tuple[str, str]]) -> dict[str, Any]:
    if len(options) <= 5:
        return buttons_screen(f"Selecione o detalhe para '{assunto}':", options)
    return select_form(
        title=f"GEDUC - {assunto}",
        name="geduc_abertura_chamado_subtema",
        key="subtema",
        field_title="Selecione a opção desejada:",
        options=options,
    )


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
            sub_options = d.SUBMENUS.get(subject)
            if sub_options:
                return pack(
                    flow_name=d.FLOW_NAME,
                    step=STEP_SUBTEMA,
                    flow_data=flow_data,
                    texts=(f"Assunto identificado: **{subject}**",),
                    screens=(_subtema_screen(subject, sub_options),),
                )
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_DETALHE,
                flow_data=flow_data,
                texts=(f"Assunto identificado: **{subject}**",),
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
                    field_title="Selecione o assunto do chamado:",
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
                        field_title="Selecione o assunto do chamado:",
                        options=d.subject_choices(),
                    )
                ],
            )
        flow_data["assunto"] = choice
        sub_options = d.SUBMENUS.get(choice)
        if sub_options:
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_SUBTEMA,
                flow_data=flow_data,
                texts=(f"Assunto selecionado: **{choice}**",),
                screens=(_subtema_screen(choice, sub_options),),
            )
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            texts=(f"Assunto selecionado: **{choice}**",),
            screens=(SCREENS[STEP_DETALHE],),
        )

    if step == STEP_SUBTEMA:
        assunto = str(flow_data.get("assunto") or "")
        sub_options = d.SUBMENUS.get(assunto, [])
        chosen = field_text(user_text, "subtema") or match_choice(user_text, sub_options)
        if not chosen:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_SUBTEMA,
                prompt=f"Selecione uma opção para {assunto}:",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[_subtema_screen(assunto, sub_options)],
            )
        flow_data["subtema"] = chosen
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DETALHE,
            flow_data=flow_data,
            texts=(f"Opção: **{chosen}**",),
            screens=(SCREENS[STEP_DETALHE],),
        )

    if step == STEP_DETALHE:
        texto = field_text(user_text, "texto") or str(form_data_of(user_text).get("texto") or "").strip()
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
        message = _submeter(info, flow_data, "")
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
            prompt="Por favor, adicione o arquivo desejado:",
            flow_data=flow_data,
            service_label=d.SERVICE_LABEL,
            resume_ui=[render_named(SCREENS, STEP_ARQUIVO)],
        )
    message = _submeter(info, flow_data, anexo)
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(message,),
        done=True,
    )
