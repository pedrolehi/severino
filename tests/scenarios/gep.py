"""Cenários de teste para os fluxos da GEP (Recursos Humanos)."""

from __future__ import annotations

from tests.scenarios.base import Scenario, Turn, TurnExpected

GEP_SCENARIOS: list[Scenario] = [
    Scenario(
        id="gep_saldo_de_horas",
        name="GEP - Consulta de Saldo de Horas",
        flow_name="saldo_de_horas",
        turns=[
            Turn(
                input_text="Qual é o meu saldo de horas?",
                description="Pergunta inicial de saldo de horas",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["banco de horas"],
                ),
            )
        ],
    ),
    Scenario(
        id="gep_abertura_chamado_crachas",
        name="GEP - Abertura de Chamado de Crachás",
        flow_name="gep_abertura_chamado_crachas",
        turns=[
            Turn(
                input_text="Preciso solicitar uma segunda via de crachá",
                description="Acionamento do fluxo de crachás",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="detalhe",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Meu crachá quebrou na catraca e preciso de uma nova via.",
                description="Preenchimento do detalhe do problema",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
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
    Scenario(
        id="gep_abertura_chamado_ponto_eletronico",
        name="GEP - Abertura de Chamado de Ponto Eletrônico",
        flow_name="gep_abertura_chamado_ponto_eletronico",
        turns=[
            Turn(
                input_text="Estou com erro no ponto eletrônico",
                description="Acionamento do fluxo de ponto eletrônico",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_ponto_eletronico",
                    flow_step="detalhe",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] O aplicativo Ponto WEB não gravou as batidas de ontem.",
                description="Preenchimento do detalhe do erro",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_ponto_eletronico",
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
    Scenario(
        id="gep_abertura_chamado_beneficios",
        name="GEP - Abertura de Chamado de Benefícios",
        flow_name="gep_abertura_chamado_beneficios",
        turns=[
            Turn(
                input_text="Gostaria de abrir um chamado sobre benefícios",
                description="Acionamento do fluxo de benefícios",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_beneficios",
                    flow_step="tema",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Cooperativa",
                description="Seleção do tema Cooperativa",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_beneficios",
                    flow_step="subtema",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Consignado",
                description="Seleção do subtema Consignado",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_beneficios",
                    flow_step="detalhe",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Gostaria de solicitar informações para empréstimo consignado.",
                description="Preenchimento do detalhe da solicitação",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_beneficios",
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
    Scenario(
        id="gep_abertura_chamado_carta_convite",
        name="GEP - Abertura de Chamado de Carta Convite",
        flow_name="gep_abertura_chamado_carta_convite",
        turns=[
            Turn(
                input_text="Preciso abrir chamado sobre carta convite",
                description="Acionamento do fluxo de carta convite",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_carta_convite",
                    flow_step="tema",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Dúvidas gerais",
                description="Seleção do tema Dúvidas gerais",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_carta_convite",
                    flow_step="subtema",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Funcionários CLT",
                description="Seleção do público Funcionários CLT",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_carta_convite",
                    flow_step="detalhe",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="[CHAMADO DE TESTE AUTOMÁTICO - FAVOR DESCONSIDERAR] Dúvida referente ao processo de emissão para docente CLT.",
                description="Preenchimento do detalhe",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_carta_convite",
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
