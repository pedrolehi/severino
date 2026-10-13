"""Cenários de teste para os fluxos da GEDUC (Gestão Educacional)."""

from __future__ import annotations

from tests.scenarios.base import Scenario, Turn, TurnExpected

GEDUC_SCENARIOS: list[Scenario] = [
    Scenario(
        id="geduc_abertura_chamado",
        name="GEDUC - Abertura de Chamado (Portarias)",
        flow_name="geduc_abertura_chamado",
        turns=[
            Turn(
                input_text="Quero abrir chamado no GEDUC sobre solicitação de portarias",
                description="Acionamento do fluxo com assunto reconhecido",
                expected=TurnExpected(
                    active_flow="geduc_abertura_chamado",
                    flow_step="subtema",
                    has_ui=True,
                    text_contains=["Solicitação de portarias"],
                ),
            ),
            Turn(
                input_text="Designação de diretor e secretário escolar",
                description="Seleção da portaria desejada no submenu",
                expected=TurnExpected(
                    active_flow="geduc_abertura_chamado",
                    flow_step="detalhe",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Solicitação de portaria para novo diretor da unidade escolar Lapa Tito.",
                description="Preenchimento do detalhe da solicitação",
                expected=TurnExpected(
                    active_flow="geduc_abertura_chamado",
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
