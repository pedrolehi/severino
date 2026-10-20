"""Cenários de teste para os fluxos da GEF (Gestão Financeira)."""

from __future__ import annotations

from tests.scenarios.base import Scenario, Turn, TurnExpected
from tests.test_mass import GEF_TEST_DATA

GEF_SCENARIOS: list[Scenario] = [
    Scenario(
        id="gef_centro_de_custo_consulta",
        name="GEF - Centro de Custo (Consulta)",
        flow_name="centro_de_custo",
        turns=[
            Turn(
                input_text="Quero consultar centro de custo",
                description="Acionamento do fluxo de centro de custo",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
                    flow_step="menu",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Consultar Centro de Custo",
                description="Escolha da opção Consultar no menu inicial",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
                    flow_step="origem",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="GD",
                description="Seleção da origem",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
                    flow_step="modalidade",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="APERFEIÇOAMENTO",
                description="Seleção da modalidade",
                expected=TurnExpected(
                    text_contains=["cursos"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_centro_de_custo_solicitar",
        name="GEF - Centro de Custo (Solicitar Abertura)",
        flow_name="centro_de_custo",
        metadata={"sem_protocolo": True},
        turns=[
            Turn(
                input_text="Quero consultar centro de custo",
                description="Acionamento do fluxo de centro de custo",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
                    flow_step="menu",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Solicitar Abertura de Centro de Custo",
                description="Escolha de solicitação no menu inicial",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["Serviços Financeiros", "cloud.sp.senac.br"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_segunda_via_nota_fiscal",
        name="GEF - Segunda Via de Nota Fiscal",
        flow_name="segunda_via_nota_fiscal",
        turns=[
            Turn(
                input_text="Quero a segunda via da nota fiscal",
                description="Acionamento do fluxo de nota fiscal",
                expected=TurnExpected(
                    active_flow="segunda_via_nota_fiscal",
                    flow_step="ask_sp",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Sim",
                description="Prestador do município de São Paulo",
                expected=TurnExpected(
                    active_flow="segunda_via_nota_fiscal",
                    flow_step="collect_data",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text=f'{{"form_data": {{"cnpj_senac": "{GEF_TEST_DATA["cnpj_senac"]}", "cnpj_cliente": "{GEF_TEST_DATA["cnpj_cliente"]}", "mes_ano": "{GEF_TEST_DATA["mes_ano"]}"}}}}',
                description="Envio do formulário com CNPJs e competência reais",
                expected=TurnExpected(
                    active_flow="segunda_via_nota_fiscal",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Encerramento da consulta",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_relatorios_orcamentarios",
        name="GEF - Relatórios Orçamentários",
        flow_name="gef_relatorios_orcamentarios",
        turns=[
            Turn(
                input_text="Solicitar relatório orçamentário",
                description="Acionamento do fluxo de relatórios orçamentários",
                expected=TurnExpected(
                    active_flow="gef_relatorios_orcamentarios",
                    flow_step="texto",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Relatório de acompanhamento orçamentário de despesas de custeio.",
                description="Preenchimento do texto",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_gestao_pagamentos",
        name="GEF - Gestão de Pagamentos",
        flow_name="gef_gestao_pagamentos",
        turns=[
            Turn(
                input_text="Problema no meu pagamento",
                description="Acionamento do fluxo de gestão de pagamentos",
                expected=TurnExpected(
                    active_flow="gef_gestao_pagamentos",
                    flow_step="tipo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Recebimento não aparece",
                description="Seleção do tipo Recebimento não aparece",
                expected=TurnExpected(
                    active_flow="gef_gestao_pagamentos",
                    flow_step="texto",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Divergência de valores de horas extras no holerite.",
                description="Preenchimento do texto",
                expected=TurnExpected(
                    active_flow="gef_gestao_pagamentos",
                    flow_step="anexo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Dispensa envio de anexo",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_cancelamento_financeiro_revisao_calculo",
        name="GEF - Cancelamento Financeiro (Revisão de Cálculo)",
        flow_name="gef_cancelamento_financeiro",
        metadata={
            "require_acesso_total": True,
            "business_params": {
                "tipo": "Revisão de Cálculo",
                "idAluno": "1140729161",
                "idCancelamento": "123456",
                "descricao": "Solicito revisão do cálculo das parcelas financeiras do cancelamento de matrícula do aluno.",
            },
        },
        turns=[
            Turn(
                input_text="Quero abrir chamado de cancelamento de matrícula",
                description="Acionamento do fluxo de cancelamento financeiro",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="tipo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Revisão de Cálculo",
                description="Seleção da situação Revisão de Cálculo",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="descricao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Solicito revisão do cálculo das parcelas financeiras do cancelamento de matrícula do aluno.",
                description="Preenchimento da descrição detalhada",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="id_aluno",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="1140729161",
                description="Envio do ID do aluno (emplid)",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="requisicao",
                    has_ui=True,
                    text_contains_any=["requisição", "cancelamento"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_cancelamento_financeiro_nao_processados",
        name="GEF - Cancelamento Financeiro (Não Processados)",
        flow_name="gef_cancelamento_financeiro",
        metadata={
            "require_acesso_total": True,
            "business_params": {
                "tipo": "Não processados",
                "lote": False,
                "idAluno": "1140729161",
                "motivoMsg": "Cancelamento não processado no portal corporativo",
            },
        },
        turns=[
            Turn(
                input_text="Abrir chamado de cancelamento não processado",
                description="Acionamento do fluxo de cancelamento financeiro",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="tipo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não processados",
                description="Seleção da situação Não processados",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="lote",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Recusa abertura por lote (individual)",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="descricao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Cancelamento não foi processado no portal corporativo do aluno.",
                description="Preenchimento da descrição",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="id_aluno",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="1140729161",
                description="Envio do ID do aluno",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="requisicao",
                    has_ui=True,
                    text_contains_any=["requisição", "cancelamento"],
                ),
            ),
        ],
    ),
]
