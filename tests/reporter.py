"""Gerador de relatórios de execução de testes E2E e tabela de limpeza no ICD."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tests.config import REPORTS_DIR
from tests.scenarios.base import CreatedTicket, ScenarioResult


class TestReporter:
    """Consolida os resultados dos testes e gera relatórios em Markdown e JSON."""

    def __init__(self, results: list[ScenarioResult], reports_dir: Path = REPORTS_DIR) -> None:
        self.results = results
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now()

    @property
    def total_scenarios(self) -> int:
        return len(self.results)

    @property
    def passed_scenarios(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_scenarios(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total_duration_ms(self) -> float:
        return sum(r.duration_ms for r in self.results)

    @property
    def all_tickets(self) -> list[CreatedTicket]:
        tickets: list[CreatedTicket] = []
        for r in self.results:
            tickets.extend(r.tickets)
        return tickets

    def generate_markdown(self) -> str:
        data_str = self.timestamp.strftime("%d/%m/%Y %H:%M:%S")
        status_geral = "PASSED ✅" if self.failed_scenarios == 0 else "FAILED ❌"

        lines: list[str] = [
            "# Relatório de Execução de Testes E2E dos Fluxos",
            "",
            f"- **Data / Hora:** {data_str}",
            f"- **Resultado Geral:** {status_geral}",
            f"- **Total de Cenários:** {self.total_scenarios}",
            f"- **Passaram:** {self.passed_scenarios} ✅",
            f"- **Falharam:** {self.failed_scenarios} ❌",
            f"- **Tempo Total:** {self.total_duration_ms / 1000:.2f}s",
            "",
            "---",
            "",
            "## ⚠️ Tabela de Limpeza no ICD (IBM Control Desk)",
            "",
        ]

        tickets = self.all_tickets
        if tickets:
            lines.extend(
                [
                    "> [!IMPORTANT]",
                    "> Os seguintes chamados foram criados durante os testes e **devem ser excluídos ou cancelados manualmente** no ICD:",
                    "",
                    "| # | Protocolo / ID no ICD | Fluxo | Assunto / Cenário | Chapa / Usuário | Data / Hora | Ação ICD |",
                    "| :- | :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for idx, t in enumerate(tickets, start=1):
                lines.append(
                    f"| {idx} | `{t.ticket_id}` | `{t.flow_name}` | {t.subject} | {t.chapa} - {t.user_name} | {t.created_at} | [ ] Excluir no ICD |"
                )
        else:
            lines.extend(
                [
                    "> [!NOTE]",
                    "> Nenhum chamado real foi aberto durante esta bateria de testes (ou os testes foram executados com mock de chamados).",
                ]
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## Resumo dos Cenários",
                "",
                "| Status | ID do Cenário | Nome do Cenário | Fluxo | Turnos | Duração |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for r in self.results:
            st = "✅ PASS" if r.passed else "❌ FAIL"
            lines.append(
                f"| {st} | `{r.scenario_id}` | {r.scenario_name} | `{r.flow_name}` | {len(r.turn_results)} | {r.duration_ms:.0f}ms |"
            )

        # Seções com falhas e detalhes
        if self.failed_scenarios > 0:
            lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## ❌ Detalhamento de Erros e Discrepâncias",
                    "",
                ]
            )
            for r in self.results:
                if r.passed:
                    continue
                lines.append(f"### Cenário: `{r.scenario_id}` ({r.scenario_name})")
                for tr in r.turn_results:
                    if tr.passed:
                        continue
                    lines.append(f"- **Turno {tr.turn_index}:** Entrada: *\"{tr.input_text}\"*")
                    for err in tr.errors:
                        lines.append(f"  - 🔴 **Erro:** {err}")
                    clean_output = tr.output_text.strip()
                    lines.append("  - 📄 **Resposta recebida na íntegra:**")
                    if "\n" in clean_output:
                        quoted_output = "\n".join(f"    > {line}" for line in clean_output.splitlines())
                        lines.append(quoted_output)
                    else:
                        lines.append(f"    > {clean_output}")
                lines.append("")

        return "\n".join(lines)

    def save(self) -> tuple[Path, Path]:
        filename_base = f"test_run_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        md_path = self.reports_dir / f"{filename_base}.md"
        json_path = self.reports_dir / f"{filename_base}.json"

        # Salva Markdown
        md_path.write_text(self.generate_markdown(), encoding="utf-8")

        # Salva JSON
        serializable_results: list[dict[str, Any]] = []
        for r in self.results:
            serializable_results.append(
                {
                    "scenario_id": r.scenario_id,
                    "scenario_name": r.scenario_name,
                    "flow_name": r.flow_name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "tickets": [
                        {
                            "ticket_id": t.ticket_id,
                            "flow_name": t.flow_name,
                            "subject": t.subject,
                            "user_name": t.user_name,
                            "chapa": t.chapa,
                            "created_at": t.created_at,
                        }
                        for t in r.tickets
                    ],
                    "turns": [
                        {
                            "turn_index": tr.turn_index,
                            "input_text": tr.input_text,
                            "passed": tr.passed,
                            "errors": tr.errors,
                            "active_flow": tr.active_flow,
                            "flow_step": tr.flow_step,
                        }
                        for tr in r.turn_results
                    ],
                }
            )

        payload_json = {
            "timestamp": self.timestamp.isoformat(),
            "total_scenarios": self.total_scenarios,
            "passed": self.passed_scenarios,
            "failed": self.failed_scenarios,
            "total_duration_ms": self.total_duration_ms,
            "results": serializable_results,
        }
        json_path.write_text(json.dumps(payload_json, indent=2, ensure_ascii=False), encoding="utf-8")

        return md_path, json_path
