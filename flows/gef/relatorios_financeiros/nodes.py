"""Runner — relatórios financeiros. Segue o Flow_GEF_R_F."""

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
    select_form,
    session_block,
)
from flows.runtime import parse_boolean
from flows.screen import load_screens, render_screen
from flows.session import acesso_relatorios, missing_fields, session_from_state
from flows.gef.relatorios_financeiros import domain as d
from graph.state import MultiAgentState

SCREENS = load_screens(Path(__file__).with_name("screens.json"))
STEP_EMITIR = "emitir"
STEP_CAIXA = "caixa"
STEP_CONFIRM_CAIXA = "confirm_caixa"
STEP_DATA = "data"
STEP_DATA_FIM = "data_fim"
STEP_CONFIRM_DATA = "confirm_data"
STEP_OUTRA = "outra"


def relatorios_financeiros_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)

    if step is None:
        missing = missing_fields(info, ("chapa", "email"))
        if missing:
            return pack(
                flow_name=d.FLOW_NAME,
                step=None,
                flow_data={},
                texts=(session_block(missing),),
                done=True,
            )
        acesso = acesso_relatorios(state)
        if not d.acesso_status_ok(acesso):
            return _done(d.UNAVAILABLE)
        if not d.acesso_total(acesso):
            return _done(d.NO_ACCESS)
        return _intro()

    if step == STEP_EMITIR:
        answer = _bool(user_text)
        if answer is None:
            return _reject(STEP_EMITIR, d.ASK_EMITIR, flow_data, _intro_ui())
        if not answer:
            return _done(d.THANKS)
        return _after_emitir(flow_data)

    if step == STEP_CAIXA:
        return _on_caixa(user_text, flow_data)

    if step == STEP_CONFIRM_CAIXA:
        answer = _bool(user_text)
        if answer is None:
            return _reject(STEP_CONFIRM_CAIXA, d.ASK_CONFIRM_CAIXA, flow_data, [_confirm_caixa_ui()])
        if not answer:
            return _caixa_menu(flow_data)
        return _ask_data(flow_data)

    if step == STEP_DATA:
        return _on_data(user_text, flow_data)

    if step == STEP_DATA_FIM:
        return _on_data_fim(user_text, flow_data)

    if step == STEP_CONFIRM_DATA:
        answer = _bool(user_text)
        if answer is None:
            return _reject(
                STEP_CONFIRM_DATA,
                d.ASK_CONFIRM_DATA,
                flow_data,
                _confirm_data_ui(flow_data),
            )
        if not answer:
            return _ask_data(flow_data)
        return _solicitar(info, flow_data)

    answer = _bool(user_text)
    if answer is None:
        return _reject(STEP_OUTRA, d.ASK_OUTRA, flow_data, [_outra_ui()])
    if answer:
        return _intro()
    return _done(d.MORE_HELP)


def _intro() -> dict:
    return pack(
        flow_name=d.FLOW_NAME,
        step=STEP_EMITIR,
        flow_data={},
        texts=(d.LISTA, d.AVISO),
        screens=(_yes_no(d.ASK_EMITIR),),
    )


def _intro_ui() -> list[dict[str, Any]]:
    return [
        {"response_type": "text", "text": d.LISTA},
        {"response_type": "text", "text": d.AVISO},
        {"response_type": "option", "title": d.ASK_EMITIR, "options": _options()},
    ]


def _after_emitir(flow_data: dict[str, Any]) -> dict:
    result = create_orchestrate_client().get_json("/gef/relatorios/conciliacao-caixa/lista")
    pairs = d.caixa_pairs(result.payload) if result.ok else []
    if not result.ok or not pairs:
        detail = "" if result.ok else f" {result.error_detail or 'lista vazia'}"
        return _done(f"{d.EMPTY_CAIXAS}{detail}")
    flow_data = {}
    flow_data["caixa_options"] = [list(item) for item in pairs]
    if len(pairs) == 1:
        flow_data["caixa"] = d.caixa_code(pairs[0][1])
        return _ask_data(flow_data)
    return _caixa_menu(flow_data)


def _caixa_menu(flow_data: dict[str, Any]) -> dict:
    options = [tuple(item) for item in flow_data.get("caixa_options") or []]
    return pack(
        flow_name=d.FLOW_NAME,
        step=STEP_CAIXA,
        flow_data=flow_data,
        screens=(
            select_form(
                title="Relatórios financeiros",
                name="relatorios_financeiros_caixa",
                key="caixa",
                field_title=d.ASK_CAIXA,
                options=options,
            ),
        ),
    )


def _on_caixa(user_text: str, flow_data: dict[str, Any]) -> dict:
    options = [tuple(item) for item in flow_data.get("caixa_options") or []]
    chosen = field_text(user_text, "caixa") or match_choice(user_text, options)
    if not chosen or chosen not in {value for _, value in options}:
        return _reject(STEP_CAIXA, d.ASK_CAIXA, flow_data, [render_screen(_caixa_ui(options))])
    flow_data["caixa"] = d.caixa_code(chosen)
    flow_data["caixa_label"] = next(label for label, value in options if value == chosen)
    return pack(
        flow_name=d.FLOW_NAME,
        step=STEP_CONFIRM_CAIXA,
        flow_data=flow_data,
        texts=(f"Caixa selecionada: {flow_data['caixa_label']}",),
        screens=(_yes_no(d.ASK_CONFIRM_CAIXA),),
    )


def _ask_data(flow_data: dict[str, Any]) -> dict:
    flow_data.pop("data_inicio", None)
    flow_data.pop("data_fim", None)
    flow_data.pop("periodo", None)
    return pack(
        flow_name=d.FLOW_NAME,
        step=STEP_DATA,
        flow_data=flow_data,
        screens=(SCREENS[STEP_DATA],),
    )


def _on_data(user_text: str, flow_data: dict[str, Any]) -> dict:
    raw = field_text(user_text, "dataRelatorio") or ""
    day = d.parse_date(raw)
    if day is None:
        return _reject(STEP_DATA, d.ASK_DATA, flow_data, [render_named(SCREENS, STEP_DATA)])
    flow_data["data_inicio"] = d.api_date(day)
    if d.needs_end_date(day):
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DATA_FIM,
            flow_data=flow_data,
            screens=(SCREENS[STEP_DATA_FIM],),
        )
    flow_data["data_fim"] = flow_data["data_inicio"]
    return _confirm_data(flow_data)


def _on_data_fim(user_text: str, flow_data: dict[str, Any]) -> dict:
    raw = field_text(user_text, "dataRelatorioFim") or ""
    day = d.parse_date(raw)
    if day is None:
        return _reject(
            STEP_DATA_FIM,
            d.ASK_DATA_FIM,
            flow_data,
            [render_named(SCREENS, STEP_DATA_FIM)],
        )
    if not d.before_today(day):
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_DATA_FIM,
            flow_data=flow_data,
            screens=(SCREENS[STEP_DATA_FIM],),
        )
    flow_data["data_fim"] = d.api_date(day)
    flow_data["periodo"] = True
    return _confirm_data(flow_data)


def _confirm_data(flow_data: dict[str, Any]) -> dict:
    inicio = d.parse_date(str(flow_data.get("data_inicio") or ""))
    fim = d.parse_date(str(flow_data.get("data_fim") or ""))
    texts: tuple[str, ...] = ()
    question = d.ASK_CONFIRM_DATA
    if flow_data.get("periodo") and inicio and fim:
        texts = (d.periodo_text(inicio, fim),)
        question = d.ASK_CONFIRM_PERIODO
    return pack(
        flow_name=d.FLOW_NAME,
        step=STEP_CONFIRM_DATA,
        flow_data=flow_data,
        texts=texts,
        screens=(_yes_no(question),),
    )


def _queue_date(raw: str) -> str:
    """Fila lê DDMMYYYY. Orchestrate só tira o hífen de dd-mm-yyyy."""
    day = d.parse_date(raw)
    if day is None:
        return raw
    return d.show_date(day)


def _solicitar(info: dict[str, str], flow_data: dict[str, Any]) -> dict:
    inicio = _queue_date(str(flow_data.get("data_inicio") or ""))
    fim = _queue_date(str(flow_data.get("data_fim") or flow_data.get("data_inicio") or ""))
    result = create_orchestrate_client().post_json(
        "/gef/relatorios/solicitar",
        {
            "chapa": info["chapa"],
            "caixa": flow_data.get("caixa"),
            "dataRelatorio": inicio,
            "dataRelatorioFim": fim,
            "email": info["email"],
        },
    )
    if not result.ok:
        detail = result.error_detail or "a integração não aceitou o pedido"
        return _done(f"Não gerei os relatórios. {detail}")
    return pack(
        flow_name=d.FLOW_NAME,
        step=STEP_OUTRA,
        flow_data=flow_data,
        texts=(d.GENERATING,),
        screens=(_yes_no(d.ASK_OUTRA),),
    )


def _done(text: str) -> dict:
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data={},
        texts=(text,),
        done=True,
    )


def _bool(user_text: str) -> bool | None:
    answer = parse_boolean(user_text)
    if answer is not None:
        return answer
    choice = match_choice(user_text, d.CONFIRM)
    if choice == "sim":
        return True
    if choice == "nao":
        return False
    return None


def _yes_no(text: str) -> dict[str, Any]:
    return buttons_screen(text, d.CONFIRM)


def _options() -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in d.CONFIRM]


def _confirm_caixa_ui() -> dict[str, Any]:
    return {"response_type": "option", "title": d.ASK_CONFIRM_CAIXA, "options": _options()}


def _outra_ui() -> dict[str, Any]:
    return {"response_type": "option", "title": d.ASK_OUTRA, "options": _options()}


def _caixa_ui(options: list[tuple[str, str]]) -> dict[str, Any]:
    return select_form(
        title="Relatórios financeiros",
        name="relatorios_financeiros_caixa",
        key="caixa",
        field_title=d.ASK_CAIXA,
        options=options,
    )


def _confirm_data_ui(flow_data: dict[str, Any]) -> list[dict[str, Any]]:
    inicio = d.parse_date(str(flow_data.get("data_inicio") or ""))
    fim = d.parse_date(str(flow_data.get("data_fim") or ""))
    question = d.ASK_CONFIRM_DATA
    ui: list[dict[str, Any]] = []
    if flow_data.get("periodo") and inicio and fim:
        question = d.ASK_CONFIRM_PERIODO
        ui.append({"response_type": "text", "text": d.periodo_text(inicio, fim)})
    ui.append({"response_type": "option", "title": question, "options": _options()})
    return ui


def _reject(
    step: str,
    prompt: str,
    flow_data: dict[str, Any],
    resume_ui: list[dict[str, Any]],
) -> dict:
    return reject(
        flow_name=d.FLOW_NAME,
        resume_step=step,
        prompt=prompt,
        flow_data=flow_data,
        service_label=d.SERVICE_LABEL,
        resume_ui=resume_ui,
    )
