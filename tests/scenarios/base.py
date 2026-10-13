"""Modelos de dados para cenários de testes conversacionais multi-turno."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TurnExpected:
    """Validações esperadas na resposta de um turno."""

    active_flow: str | None = None
    flow_step: str | None = None
    text_contains: list[str] = field(default_factory=list)
    text_contains_any: list[str] = field(default_factory=list)
    has_ui: bool | None = None
    ui_component: str | None = None  # "form", "buttons", "select"
    is_done: bool | None = None


@dataclass
class Turn:
    """Representa um turno de conversa na simulação do usuário."""

    input_text: str
    expected: TurnExpected = field(default_factory=TurnExpected)
    description: str = ""


@dataclass
class CreatedTicket:
    """Chamado/Protocolo identificado para rastreamento e limpeza manual no ICD."""

    ticket_id: str
    flow_name: str
    subject: str
    user_name: str
    chapa: str
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y %H:%M:%S"))


@dataclass
class TurnResult:
    """Resultado da execução de um turno."""

    turn_index: int
    input_text: str
    output_text: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    ticket: CreatedTicket | None = None
    active_flow: str | None = None
    flow_step: str | None = None
    ui_blocks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScenarioResult:
    """Resultado consolidado da execução de um cenário multi-turno."""

    scenario_id: str
    scenario_name: str
    flow_name: str
    passed: bool
    duration_ms: float
    turn_results: list[TurnResult] = field(default_factory=list)
    tickets: list[CreatedTicket] = field(default_factory=list)


@dataclass
class Scenario:
    """Definição de um cenário de teste ponta a ponta."""

    id: str
    name: str
    flow_name: str
    turns: list[Turn]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "flow_name": self.flow_name,
            "metadata": self.metadata,
            "turns": [
                {
                    "input_text": t.input_text,
                    "description": t.description,
                    "expected": {
                        "active_flow": t.expected.active_flow,
                        "flow_step": t.expected.flow_step,
                        "text_contains": t.expected.text_contains,
                        "text_contains_any": t.expected.text_contains_any,
                        "has_ui": t.expected.has_ui,
                        "ui_component": t.expected.ui_component,
                        "is_done": t.expected.is_done,
                    },
                }
                for t in self.turns
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario:
        turns = []
        for t_data in data.get("turns", []):
            exp_data = t_data.get("expected") or {}
            exp = TurnExpected(
                active_flow=exp_data.get("active_flow"),
                flow_step=exp_data.get("flow_step"),
                text_contains=exp_data.get("text_contains") or [],
                text_contains_any=exp_data.get("text_contains_any") or [],
                has_ui=exp_data.get("has_ui"),
                ui_component=exp_data.get("ui_component"),
                is_done=exp_data.get("is_done"),
            )
            turns.append(
                Turn(
                    input_text=str(t_data.get("input_text", "")),
                    description=str(t_data.get("description", "")),
                    expected=exp,
                )
            )
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            flow_name=str(data.get("flow_name", "")),
            metadata=dict(data.get("metadata", {})),
            turns=turns,
        )


def load_scenarios_from_json(file_path: Any) -> list[Scenario]:
    """Carrega lista de cenários a partir de um arquivo JSON estruturado."""
    import json
    from pathlib import Path

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de cenários não encontrado: {path}")

    content = json.loads(path.read_text(encoding="utf-8"))
    raw_list = content if isinstance(content, list) else content.get("scenarios", [])
    return [Scenario.from_dict(item) for item in raw_list if isinstance(item, dict)]


def save_scenarios_to_json(scenarios: list[Scenario], file_path: Any) -> None:
    """Salva lista de cenários em um arquivo JSON formatado."""
    import json
    from pathlib import Path

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0",
        "description": "Massa de testes E2E do assistente Senac extraída do MongoDB e catálogo corporativo",
        "total_scenarios": len(scenarios),
        "scenarios": [s.to_dict() for s in scenarios],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
