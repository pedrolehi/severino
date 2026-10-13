"""Cenários de teste para os fluxos da GPG (Gestão de Documentos)."""

from __future__ import annotations

from tests.scenarios.base import Scenario, Turn, TurnExpected

GPG_SCENARIOS: list[Scenario] = [
    Scenario(
        id="gpg_consulta_documentos",
        name="GPG - Consulta de Documentos",
        flow_name="consulta_documentos",
        turns=[
            Turn(
                input_text="Quero consultar meus documentos",
                description="Acionamento do fluxo de consulta de documentos",
                expected=TurnExpected(
                    active_flow="consulta_documentos",
                    flow_step="keyword",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="comprovante",
                description="Envio da palavra-chave de busca",
                expected=TurnExpected(
                    active_flow="consulta_documentos",
                    flow_step="next",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Encerrar",
                description="Encerramento da consulta",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["Consulta encerrada"],
                ),
            ),
        ],
    ),
]
