"""Runner — centro de custo. Selects em cadeia a partir das listas GEF."""

from __future__ import annotations

from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import buttons_screen, field_text, last_user_text, match_choice, pack, reject, select_form
from flows.payload import option_pairs
from flows.gef.centro_de_custo import domain as d
from graph.state import MultiAgentState

STEP_ORIGEM = "origem"
STEP_MODALIDADE = "modalidade"
STEP_CURSO = "curso"
STEP_FICHA = "ficha"
STEP_NEXT = "next"


def _choices(path: str, params: dict[str, str] | None = None) -> tuple[list[tuple[str, str]], str | None]:
    result = create_orchestrate_client().get_json(path, params)
    if not result.ok:
        return [], result.error_detail or "erro desconhecido"
    pairs = option_pairs(result.payload)
    if not pairs:
        return [], "A lista veio vazia."
    return pairs, None


def _select(step: str, title: str, field_title: str, options: list[tuple[str, str]]) -> dict[str, Any]:
    return select_form(
        title=title,
        name=f"centro_de_custo_{step}",
        key=step,
        field_title=field_title,
        options=options,
    )


def centro_de_custo_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])

    if step is None or step == STEP_ORIGEM and not flow_data.get("_shown"):
        if step is None:
            options, error = _choices("/gef/lista-origem")
            if error or not options:
                return pack(
                    flow_name=d.FLOW_NAME,
                    step=None,
                    flow_data={},
                    texts=(f"Não carreguei as origens. {error or 'lista vazia'}",),
                    done=True,
                )
            flow_data["origem_options"] = options
            flow_data["_shown"] = True
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_ORIGEM,
                flow_data=flow_data,
                screens=(_select(STEP_ORIGEM, "Centro de custo", "Origem", options),),
            )

    if step == STEP_ORIGEM:
        options = [tuple(item) for item in flow_data.get("origem_options") or []]
        chosen = field_text(user_text, STEP_ORIGEM) or match_choice(user_text, options)
        if not chosen:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_ORIGEM,
                prompt="Origem",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[_select(STEP_ORIGEM, "Centro de custo", "Origem", options)],
            )
        flow_data["origem"] = chosen
        next_options, error = _choices("/gef/lista-modalidade", {"origem": chosen})
        if error or not next_options:
            return pack(
                flow_name=d.FLOW_NAME,
                step=None,
                flow_data=flow_data,
                texts=(f"Não carreguei as modalidades. {error or 'lista vazia'}",),
                done=True,
            )
        flow_data["modalidade_options"] = next_options
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_MODALIDADE,
            flow_data=flow_data,
            screens=(_select(STEP_MODALIDADE, "Centro de custo", "Modalidade", next_options),),
        )

    if step == STEP_MODALIDADE:
        options = [tuple(item) for item in flow_data.get("modalidade_options") or []]
        chosen = field_text(user_text, STEP_MODALIDADE) or match_choice(user_text, options)
        if not chosen:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_MODALIDADE,
                prompt="Modalidade",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[_select(STEP_MODALIDADE, "Centro de custo", "Modalidade", options)],
            )
        flow_data["modalidade"] = chosen
        next_options, error = _choices(
            "/gef/lista-curso",
            {"origem": str(flow_data.get("origem") or ""), "modalidade": chosen},
        )
        if error or not next_options:
            return pack(
                flow_name=d.FLOW_NAME,
                step=None,
                flow_data=flow_data,
                texts=(f"Não carreguei os cursos. {error or 'lista vazia'}",),
                done=True,
            )
        flow_data["curso_options"] = next_options
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_CURSO,
            flow_data=flow_data,
            screens=(_select(STEP_CURSO, "Centro de custo", "Curso", next_options),),
        )

    if step == STEP_CURSO:
        options = [tuple(item) for item in flow_data.get("curso_options") or []]
        chosen = field_text(user_text, STEP_CURSO) or match_choice(user_text, options)
        if not chosen:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_CURSO,
                prompt="Curso",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[_select(STEP_CURSO, "Centro de custo", "Curso", options)],
            )
        flow_data["curso"] = chosen
        fichas, error = _choices(
            "/gef/lista-ficha-tecnica",
            {
                "origem": str(flow_data.get("origem") or ""),
                "modalidade": str(flow_data.get("modalidade") or ""),
                "curso": chosen,
            },
        )
        if error or not fichas:
            return pack(
                flow_name=d.FLOW_NAME,
                step=None,
                flow_data=flow_data,
                texts=(f"Não encontrei ficha técnica. {error or 'lista vazia'}",),
                done=True,
            )
        flow_data["ficha_options"] = fichas
        if len(fichas) == 1:
            return pack(
                flow_name=d.FLOW_NAME,
                step=STEP_NEXT,
                flow_data=flow_data,
                texts=(fichas[0][0],),
                screens=(buttons_screen("O que deseja fazer agora?", d.NEXT),),
            )
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_FICHA,
            flow_data=flow_data,
            screens=(_select(STEP_FICHA, "Centro de custo", "Ficha técnica", fichas),),
        )

    if step == STEP_FICHA:
        options = [tuple(item) for item in flow_data.get("ficha_options") or []]
        chosen = field_text(user_text, STEP_FICHA) or match_choice(user_text, options)
        picked = next((item for item in options if item[1] == chosen or item[0] == chosen), None)
        if picked is None:
            return reject(
                flow_name=d.FLOW_NAME,
                resume_step=STEP_FICHA,
                prompt="Ficha técnica",
                flow_data=flow_data,
                service_label=d.SERVICE_LABEL,
                resume_ui=[_select(STEP_FICHA, "Centro de custo", "Ficha técnica", options)],
            )
        return pack(
            flow_name=d.FLOW_NAME,
            step=STEP_NEXT,
            flow_data=flow_data,
            texts=(picked[0],),
            screens=(buttons_screen("O que deseja fazer agora?", d.NEXT),),
        )

    choice = match_choice(user_text, d.NEXT)
    if choice == "de_novo":
        return centro_de_custo_node({**state, "flow_step": None, "flow_data": {}})
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
