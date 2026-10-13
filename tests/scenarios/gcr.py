"""Cenários de teste para os fluxos da GCR (Relacionamento e Atendimento)."""

from __future__ import annotations

from tests.scenarios.base import Scenario, Turn, TurnExpected

GCR_SCENARIOS: list[Scenario] = [
    Scenario(
        id="gcr_abertura_chamado",
        name="GCR - Abertura de Chamado",
        flow_name="gcr_abertura_chamado",
        turns=[
            Turn(
                input_text="Preciso abrir chamado no GCR",
                description="Acionamento do fluxo de abertura de chamado GCR",
                expected=TurnExpected(
                    active_flow="gcr_abertura_chamado",
                    flow_step="detalhe",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Dúvida de cliente presencial referente a pendência cadastral na unidade.",
                description="Preenchimento do detalhe do problema",
                expected=TurnExpected(
                    active_flow="gcr_abertura_chamado",
                    flow_step="ask_anexo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Dispensa envio de arquivo",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
]
