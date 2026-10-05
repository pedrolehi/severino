"""Runner — consulta de documentos GPG."""

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
    reject,
    render_named,
    session_block,
)
from flows.payload import documentos_text
from flows.screen import load_screens, screen_text
from flows.session import missing_fields, session_from_state
from flows.gpg.consulta_documentos import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_KEYWORD = "keyword"
STEP_NEXT = "next"


def consulta_documentos_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)

    if step is None:
        missing = missing_fields(info, ("chapa",))
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
            step=STEP_KEYWORD,
            flow_data={},
            screens=(SCREENS[STEP_KEYWORD],),
        )

    if step == STEP_KEYWORD:
        keyword = field_text(user_text, "keyword")
        if not keyword:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_KEYWORD,
                prompt=screen_text(SCREENS[STEP_KEYWORD]),
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[render_named(SCREENS, STEP_KEYWORD)],
            )
        result = create_orchestrate_client().consulta_documentos(
            chapa=info["chapa"],
            keyword=keyword,
        )
        if not result.ok:
            text = documentos_text({}) if not result.error_detail else result.error_detail
            message = f"Não consultei os documentos. {text}"
        else:
            message = documentos_text(result.payload)
        flow_data["keyword"] = keyword
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_NEXT,
            flow_data=flow_data,
            texts=(message,),
            screens=(buttons_screen("O que deseja fazer agora?", d.NEXT),),
        )

    choice = match_choice(user_text, d.NEXT)
    if choice == "de_novo":
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_KEYWORD,
            flow_data={},
            screens=(SCREENS[STEP_KEYWORD],),
        )
    if choice == "encerrar":
        return pack(
            flow_name=d.FLOW_NAME,
            step=None,
            flow_data=flow_data,
            texts=("Consulta encerrada.",),
            done=True,
        )
    return reject(
        flow_name=d.FLOW_NAME,
        resume_step=STEP_NEXT,
        prompt="O que deseja fazer agora?",
        flow_data=flow_data,
        service_label=d.SERVICE_LABEL,
        resume_ui=[buttons_screen("O que deseja fazer agora?", d.NEXT)],
    )
