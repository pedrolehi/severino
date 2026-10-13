"""Motor de execução dos testes conversacionais multi-turno (Runner)."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from core.hub import build_thread_id, get_graph
from flows.session import normalize_user_info
from tests.config import ASSISTANT_ID, TEST_USER_INFO
from tests.scenarios.base import CreatedTicket, Scenario, ScenarioResult, Turn, TurnResult

_TICKET_REGEX = re.compile(
    r"(?:protocolo|chamado|ticket)[\s:]+([A-Za-z0-9_\-\.]+)",
    re.IGNORECASE,
)


def _extract_ticket_id(text: str) -> str | None:
    lower = text.lower()
    if "não abri o chamado" in lower or "não abri chamado" in lower:
        return None

    # Padrão primário dos nossos fluxos: "Chamado aberto. Protocolo: <ticket_id>."
    match = re.search(r"Protocolo:\s*([A-Za-z0-9_\-\.]+)", text, re.IGNORECASE)
    if match:
        val = match.group(1).strip().rstrip(".")
        if val.lower() not in {"mock", "erro", "nenhum", "a", "o", "de", "relacionado"} and (
            any(ch.isdigit() for ch in val) or val.startswith("SNC") or val.startswith("MOCK")
        ):
            return val

    # Padrão secundário para códigos com dígitos ou prefixo SNC/MOCK
    for candidate in re.findall(
        r"(?:protocolo|chamado|ticket)[\s:]+([A-Za-z0-9_\-\.]+)", text, re.IGNORECASE
    ):
        cleaned = candidate.strip().rstrip(".")
        if any(ch.isdigit() for ch in cleaned) or cleaned.startswith("SNC") or cleaned.startswith("MOCK"):
            return cleaned

    return None


def _last_ai_message(result: dict[str, Any]) -> AIMessage | None:
    messages = result.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _response_text(result: dict[str, Any]) -> str:
    ai = _last_ai_message(result)
    if not ai:
        return ""
    content = ai.content
    return content if isinstance(content, str) else str(content)


def _response_ui(result: dict[str, Any]) -> list[dict[str, Any]]:
    ai = _last_ai_message(result)
    if not ai:
        return []
    raw = (ai.additional_kwargs or {}).get("ui")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


class FlowTestRunner:
    """Executa cenários de teste contra o LangGraph em tempo real."""

    def __init__(self, assistant_id: str = ASSISTANT_ID) -> None:
        self.assistant_id = assistant_id
        self.graph = get_graph(assistant_id)

    def run_scenario(self, scenario: Scenario) -> ScenarioResult:
        session_id = f"test_{scenario.id}_{uuid.uuid4().hex[:8]}"
        thread_id = build_thread_id(self.assistant_id, session_id)
        config = {"configurable": {"thread_id": thread_id}}

        t0 = time.perf_counter()
        turn_results: list[TurnResult] = []
        created_tickets: list[CreatedTicket] = []
        all_passed = True

        # Mescla dados específicos do cenário com os dados base do colaborador (preservando acessoRelatorios, etc.)
        merged_user = dict(TEST_USER_INFO)
        scenario_user = scenario.metadata.get("user_info")
        if scenario_user:
            if "DADOS" in merged_user and isinstance(merged_user["DADOS"], dict):
                merged_user["DADOS"].update(scenario_user)
            else:
                merged_user.update(scenario_user)
            if "acessoRelatorios" in scenario_user:
                merged_user["acessoRelatorios"] = scenario_user["acessoRelatorios"]
        active_user_info = merged_user

        for idx, turn in enumerate(scenario.turns, start=1):
            payload = {
                "assistant_id": self.assistant_id,
                "session_id": session_id,
                "app_env": "hml",
                "rag_stream": False,
                "user_info": normalize_user_info(active_user_info),
                "messages": [HumanMessage(content=turn.input_text)],
            }

            try:
                result = self.graph.invoke(payload, config=config)
            except Exception as exc:  # noqa: BLE001
                all_passed = False
                turn_results.append(
                    TurnResult(
                        turn_index=idx,
                        input_text=turn.input_text,
                        output_text=f"EXCEÇÃO: {exc}",
                        passed=False,
                        errors=[f"Erro durante graph.invoke: {exc}"],
                    )
                )
                break

            output_text = _response_text(result)
            ui_blocks = _response_ui(result)
            active_flow = result.get("active_flow")
            flow_step = result.get("flow_step")

            errors: list[str] = []

            # Validações esperadas
            exp = turn.expected
            if exp.active_flow is not None and active_flow != exp.active_flow:
                errors.append(f"Esperava active_flow='{exp.active_flow}', mas recebeu '{active_flow}'")

            if exp.flow_step is not None and flow_step != exp.flow_step:
                errors.append(f"Esperava flow_step='{exp.flow_step}', mas recebeu '{flow_step}'")

            if exp.is_done is True and (active_flow is not None or flow_step is not None):
                errors.append(f"Esperava fluxo concluído, mas active_flow='{active_flow}', flow_step='{flow_step}'")

            if exp.has_ui is True and not ui_blocks:
                errors.append("Esperava blocos de interface (UI/screens), mas nenhum foi retornado")

            if exp.has_ui is False and ui_blocks:
                errors.append("Não esperava blocos de interface (UI), mas blocos foram retornados")

            for required_substr in exp.text_contains:
                if required_substr.casefold() not in output_text.casefold():
                    errors.append(f"Texto não contém '{required_substr}'. Resposta recebida: {output_text}")

            if exp.text_contains_any:
                matched_any = any(term.casefold() in output_text.casefold() for term in exp.text_contains_any)
                if not matched_any:
                    errors.append(
                        f"Texto não contém nenhum dos termos esperados {exp.text_contains_any}. Resposta recebida: {output_text}"
                    )

            # Captura de ticket gerado
            ticket: CreatedTicket | None = None
            raw_ticket_id = _extract_ticket_id(output_text)
            if raw_ticket_id:
                user_dados = (active_user_info.get("DADOS") or active_user_info) if isinstance(active_user_info, dict) else {}
                ticket = CreatedTicket(
                    ticket_id=raw_ticket_id,
                    flow_name=scenario.flow_name,
                    subject=scenario.name,
                    user_name=str(user_dados.get("NOME") or "QA Teste"),
                    chapa=str(user_dados.get("CHAPA") or "99999"),
                )
                created_tickets.append(ticket)

            turn_passed = len(errors) == 0
            if not turn_passed:
                all_passed = False

            turn_results.append(
                TurnResult(
                    turn_index=idx,
                    input_text=turn.input_text,
                    output_text=output_text,
                    passed=turn_passed,
                    errors=errors,
                    ticket=ticket,
                    active_flow=active_flow,
                    flow_step=flow_step,
                    ui_blocks=ui_blocks,
                )
            )

        duration_ms = (time.perf_counter() - t0) * 1000
        return ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            flow_name=scenario.flow_name,
            passed=all_passed,
            duration_ms=duration_ms,
            turn_results=turn_results,
            tickets=created_tickets,
        )

    def run_all(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        return [self.run_scenario(s) for s in scenarios]
