"""Script de Agregação e Construção da Massa de Testes Reais a partir do MongoDB.

Conecta ao cluster MongoDB corporativo do Senac (banco 'orchestrate' e coleções
'sessionconversations', 'sessions', 'messages_*'), aplica aggregation pipelines
para extrair conversas com sucesso, turnos de usuário, dados cadastrais e
parâmetros de negócio (ex: idAluno, idCancelamento, CNPJs, competência, etc.).

Exporta um arquivo JSON estruturado em formato compatível com o runner de testes:
    tests/fixtures/real_test_scenarios.json

Uso:
    python scripts/mongo_dataset_aggregator.py --summary
    python scripts/mongo_dataset_aggregator.py --export tests/fixtures/real_test_scenarios.json
    python scripts/mongo_dataset_aggregator.py --theme gef --export tests/fixtures/real_test_scenarios.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

from tests.scenarios.base import Scenario, Turn, TurnExpected, save_scenarios_to_json
from tests.test_mass import GEF_TEST_DATA, TEST_COLLABORATOR

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None  # type: ignore


CANONICAL_SCENARIOS: list[Scenario] = [
    Scenario(
        id="gef_cancelamento_financeiro_revisao_calculo",
        name="GEF - Cancelamento Financeiro (Revisão de Cálculo)",
        flow_name="gef_cancelamento_financeiro",
        metadata={
            "source": "catalogo_intranet_icd",
            "classificationId": "SNC_INT_00200601",
            "assunto": "Cancelamento de matrícula",
            "user_info": {
                "chapa": TEST_COLLABORATOR["chapa"],
                "nome": TEST_COLLABORATOR["nome"],
                "email": TEST_COLLABORATOR["email"],
                "cpf": TEST_COLLABORATOR["cpf"],
                "unidade": TEST_COLLABORATOR["unidade"],
            },
            "business_params": {
                "tipo": "Revisão de Cálculo",
                "idAluno": "1140729161",
                "inscricao": "INS-001",
                "requisicao": "REQ-001",
                "idCancelamento": "123456",
                "motivoDesligamento": "Revisão de Cálculo",
                "situacaoSolicitacao": "Revisão do Cálculo",
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
                description="Seleção do tipo Revisão de Cálculo",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="descricao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Solicito revisão do cálculo das parcelas financeiras do cancelamento de matrícula do aluno.",
                description="Preenchimento da descrição detalhada da solicitação",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="id_aluno",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="1140729161",
                description="Envio do ID do aluno (emplid TOTVS)",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Dispensa envio de arquivo em anexo",
                expected=TurnExpected(
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="123456",
                description="Envio do ID do cancelamento para fechar os requisitos do chamado no ICD",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_cancelamento_financeiro_nao_processados",
        name="GEF - Cancelamento Financeiro (Não Processados)",
        flow_name="gef_cancelamento_financeiro",
        metadata={
            "source": "catalogo_intranet_icd",
            "classificationId": "SNC_INT_00200601",
            "assunto": "Cancelamento de matrícula",
            "user_info": {
                "chapa": TEST_COLLABORATOR["chapa"],
                "nome": TEST_COLLABORATOR["nome"],
                "email": TEST_COLLABORATOR["email"],
                "cpf": TEST_COLLABORATOR["cpf"],
                "unidade": TEST_COLLABORATOR["unidade"],
            },
            "business_params": {
                "tipo": "Não processados",
                "lote": False,
                "idAluno": "1140729161",
                "motivoMsg": "Cancelamento não processado no portal corporativo",
                "situacaoSolicitacao": "Cancelamento Não Processado",
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
                description="Seleção do tipo Não processados",
                expected=TurnExpected(
                    active_flow="gef_cancelamento_financeiro",
                    flow_step="lote",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Seleção de abertura individual (sem lote)",
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
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Dispensa envio de arquivo anexo",
                expected=TurnExpected(
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Bloqueio de sistema no lançamento do cancelamento",
                description="Preenchimento do motivo-mensagem para registro no ICD",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_segunda_via_nota_fiscal",
        name="GEF - Segunda Via de Nota Fiscal",
        flow_name="segunda_via_nota_fiscal",
        metadata={
            "source": "catalogo_intranet_icd",
            "user_info": {
                "chapa": TEST_COLLABORATOR["chapa"],
                "nome": TEST_COLLABORATOR["nome"],
                "email": TEST_COLLABORATOR["email"],
                "cpf": TEST_COLLABORATOR["cpf"],
                "unidade": TEST_COLLABORATOR["unidade"],
            },
            "business_params": {
                "cnpj_prestador": GEF_TEST_DATA["cnpj_senac"],
                "cnpj_tomador": GEF_TEST_DATA["cnpj_cliente"],
                "mes_ano": GEF_TEST_DATA["mes_ano"],
            },
        },
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
                description="Confirmação de que o prestador pertence ao município de São Paulo",
                expected=TurnExpected(
                    active_flow="segunda_via_nota_fiscal",
                    flow_step="collect_data",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text=f'{{"form_data": {{"cnpj_senac": "{GEF_TEST_DATA["cnpj_senac"]}", "cnpj_cliente": "{GEF_TEST_DATA["cnpj_cliente"]}", "mes_ano": "{GEF_TEST_DATA["mes_ano"]}"}}}}',
                description="Envio dos dados do formulário com CNPJs reais do Senac e competência",
                expected=TurnExpected(
                    active_flow="segunda_via_nota_fiscal",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Não",
                description="Encerramento do atendimento",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_centro_de_custo_consulta",
        name="GEF - Centro de Custo (Consulta)",
        flow_name="centro_de_custo",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "origem": "GD",
                "modalidade": "APERFEIÇOAMENTO",
                "curso": "Administração",
            },
        },
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
                description="Seleção da origem (Gerência de Desenvolvimento)",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
                    flow_step="modalidade",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="APERFEIÇOAMENTO",
                description="Seleção da modalidade de ensino",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
                    flow_step="curso",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Administração",
                description="Seleção do curso",
                expected=TurnExpected(
                    active_flow="centro_de_custo",
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
    Scenario(
        id="gef_centro_de_custo_solicitar",
        name="GEF - Centro de Custo (Solicitar Abertura)",
        flow_name="centro_de_custo",
        metadata={
            "source": "catalogo_intranet_icd",
        },
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
                description="Escolha de solicitação de abertura",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["Serviços Financeiros", "cloud.sp.senac.br"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gef_relatorios_orcamentarios",
        name="GEF - Relatórios Orçamentários",
        flow_name="gef_relatorios_orcamentarios",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "texto": "Relatório de acompanhamento orçamentário de despesas de custeio.",
            },
        },
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
                description="Preenchimento do texto explicativo",
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
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "tipo": "Recebimento não aparece",
                "texto": "Divergência de valores de horas extras no holerite.",
                "anexo": False,
            },
        },
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
                description="Seleção do tipo de problema de pagamento",
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
                description="Dispensa envio de arquivo anexo",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_cracha_provisorio",
        name="GEP - Crachá Provisório",
        flow_name="gep_abertura_chamado_crachas",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "motivo": "Esquecimento",
                "tipo": "Provisório",
            },
        },
        turns=[
            Turn(
                input_text="Preciso de um crachá provisório",
                description="Acionamento do fluxo de crachás",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="tipo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Crachá Provisório",
                description="Seleção da opção provisório",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="motivo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Esquecimento",
                description="Seleção do motivo esquecimento",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="confirmacao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Confirmar",
                description="Confirmação e abertura do chamado",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_segunda_via_cracha",
        name="GEP - Segunda Via de Crachá",
        flow_name="gep_abertura_chamado_crachas",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "motivo": "Perda",
                "tipo": "Segunda via",
            },
        },
        turns=[
            Turn(
                input_text="Perdi meu crachá funcional",
                description="Acionamento por perda de crachá",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="tipo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Segunda via",
                description="Seleção da segunda via",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="motivo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Perda",
                description="Seleção do motivo perda",
                expected=TurnExpected(
                    active_flow="gep_abertura_chamado_crachas",
                    flow_step="confirmacao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Confirmar",
                description="Confirmação e abertura do chamado",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_espelho_ponto",
        name="GEP - Consulta Espelho de Ponto",
        flow_name="gep_espelho_ponto",
        metadata={
            "source": "catalogo_intranet_icd",
        },
        turns=[
            Turn(
                input_text="Quero ver meu espelho de ponto",
                description="Acionamento do fluxo de espelho de ponto",
                expected=TurnExpected(
                    active_flow="gep_espelho_ponto",
                    flow_step="competencia",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Mês atual",
                description="Seleção da competência atual",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_ajuste_ponto",
        name="GEP - Ajuste de Batida de Ponto",
        flow_name="gep_ajuste_ponto",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "data": "10/10/2026",
                "horario": "08:00",
                "motivo": "Esqueci de registrar o ponto ao chegar na unidade",
            },
        },
        turns=[
            Turn(
                input_text="Esqueci de bater ponto ontem",
                description="Acionamento do fluxo de ajuste de ponto",
                expected=TurnExpected(
                    active_flow="gep_ajuste_ponto",
                    flow_step="data",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="10/10/2026",
                description="Informe da data do ajuste",
                expected=TurnExpected(
                    active_flow="gep_ajuste_ponto",
                    flow_step="tipo_batida",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Entrada",
                description="Seleção da batida de entrada",
                expected=TurnExpected(
                    active_flow="gep_ajuste_ponto",
                    flow_step="horario",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="08:00",
                description="Informe do horário correto",
                expected=TurnExpected(
                    active_flow="gep_ajuste_ponto",
                    flow_step="justificativa",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Esqueci de registrar o ponto ao chegar na unidade",
                description="Envio da justificativa",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_beneficios_transporte",
        name="GEP - Benefícios (Vale Transporte)",
        flow_name="gep_beneficios",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "tipo_beneficio": "Vale Transporte",
                "solicitacao": "Alteração de trajeto de transporte público",
            },
        },
        turns=[
            Turn(
                input_text="Preciso alterar meu vale transporte",
                description="Acionamento do fluxo de benefícios",
                expected=TurnExpected(
                    active_flow="gep_beneficios",
                    flow_step="tipo",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Vale Transporte",
                description="Seleção do benefício de transporte",
                expected=TurnExpected(
                    active_flow="gep_beneficios",
                    flow_step="descricao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Mudança de residência necessitando nova linha de ônibus.",
                description="Descrição da alteração",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_carta_convite",
        name="GEP - Carta Convite para Evento",
        flow_name="gep_carta_convite",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "evento": "Simpósio Estadual de Educação Profissional",
                "data": "20/11/2026",
                "local": "São Paulo - CAS",
            },
        },
        turns=[
            Turn(
                input_text="Preciso emitir uma carta convite",
                description="Acionamento do fluxo de carta convite",
                expected=TurnExpected(
                    active_flow="gep_carta_convite",
                    flow_step="evento",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Simpósio Estadual de Educação Profissional",
                description="Nome do evento",
                expected=TurnExpected(
                    active_flow="gep_carta_convite",
                    flow_step="data",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="20/11/2026",
                description="Data do evento",
                expected=TurnExpected(
                    active_flow="gep_carta_convite",
                    flow_step="local",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="São Paulo - CAS",
                description="Local do evento",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gep_saldo_horas",
        name="GEP - Saldo de Banco de Horas",
        flow_name="gep_saldo_horas",
        metadata={
            "source": "catalogo_intranet_icd",
        },
        turns=[
            Turn(
                input_text="Qual é o meu saldo de banco de horas?",
                description="Consulta do extrato de banco de horas",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
    Scenario(
        id="geduc_atualizacao_concluintes",
        name="GEDUC - Atualização de Concluintes na SEE/SP",
        flow_name="geduc_portarias_mec",
        metadata={
            "source": "catalogo_intranet_icd",
            "classificationId": "SNC_INT_00401904",
            "business_params": {
                "tipoAlteracao": "Nome",
                "nomeAluno": "Aluno Concluinte Senac",
                "rg": "12345678",
                "emplid": "1140729161",
            },
        },
        turns=[
            Turn(
                input_text="Atualizar dados de aluno concluinte na SEE",
                description="Acionamento do fluxo GEDUC de concluintes",
                expected=TurnExpected(
                    active_flow="geduc_portarias_mec",
                    flow_step="tipo_alteracao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Nome",
                description="Seleção do tipo de alteração cadastral",
                expected=TurnExpected(
                    active_flow="geduc_portarias_mec",
                    flow_step="dados_aluno",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text='{"nomeAluno": "Aluno Concluinte Senac", "rg": "12345678", "emplid": "1140729161"}',
                description="Envio dos dados cadastrais do aluno concluinte",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gcr_chamado_geral",
        name="GCR - Abertura de Chamado Geral",
        flow_name="gcr_abertura_chamado",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "assunto": "Solicitação de suporte a recursos de TI",
                "descricao": "Configuração de ponto de rede e monitor de apoio",
            },
        },
        turns=[
            Turn(
                input_text="Quero abrir um chamado geral",
                description="Acionamento do fluxo da GCR",
                expected=TurnExpected(
                    active_flow="gcr_abertura_chamado",
                    flow_step="assunto",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Solicitação de suporte a recursos de TI",
                description="Assunto do chamado",
                expected=TurnExpected(
                    active_flow="gcr_abertura_chamado",
                    flow_step="descricao",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Configuração de ponto de rede e monitor de apoio na sala 204.",
                description="Descrição da solicitação",
                expected=TurnExpected(
                    is_done=True,
                    text_contains=["protocolo"],
                ),
            ),
        ],
    ),
    Scenario(
        id="gpg_informe_rendimentos",
        name="GPG - Informe de Rendimentos IRPF",
        flow_name="gpg_documentos",
        metadata={
            "source": "catalogo_intranet_icd",
            "business_params": {
                "tipo_documento": "Informe de Rendimentos",
                "ano_base": "2024",
            },
        },
        turns=[
            Turn(
                input_text="Preciso do meu informe de rendimentos para o imposto de renda",
                description="Acionamento do fluxo de documentos de pessoal",
                expected=TurnExpected(
                    active_flow="gpg_documentos",
                    flow_step="tipo_documento",
                    has_ui=True,
                ),
            ),
            Turn(
                input_text="Informe de Rendimentos",
                description="Seleção do documento",
                expected=TurnExpected(
                    is_done=True,
                ),
            ),
        ],
    ),
]


class MongoDatasetAggregator:
    """Extrai conversas com sucesso do MongoDB e mescla com a base canônica."""

    def __init__(self, uri: str | None = None) -> None:
        self.uri = uri or os.getenv("MONGODB_URI", "").strip()
        self.client: MongoClient | None = None

    def connect(self) -> bool:
        if not self.uri:
            print("⚠️ Aviso: MONGODB_URI não configurada no .env.")
            return False
        if MongoClient is None:
            print("⚠️ Aviso: 'pymongo' não está instalado.")
            return False
        try:
            print("🔌 Conectando ao MongoDB corporativo...")
            self.client = MongoClient(
                self.uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000,
            )
            self.client.admin.command("ping")
            print("✅ Conectado ao MongoDB com sucesso.")
            return True
        except Exception as exc:
            print(f"⚠️ Não foi possível conectar ao cluster MongoDB corporativo no momento: {exc}")
            print("ℹ️ O agregador utilizará o catálogo canônico de homologação e histórico registrado.")
            self.client = None
            return False

    def aggregate_successful_conversations(self, limit: int = 200) -> list[Scenario]:
        """Executa aggregation pipeline nas coleções do banco 'orchestrate'."""
        if not self.client:
            return []

        scenarios_found: list[Scenario] = []
        db_candidates = ["orchestrate", "senac_orchestrate", "vectory"]
        try:
            existing_dbs = self.client.list_database_names()
            db_candidates = [d for d in db_candidates if d in existing_dbs] or ["orchestrate"]
        except Exception:
            pass

        target_collections = ["sessionconversations", "sessions", "messages_intranet"]

        for db_name in db_candidates:
            db = self.client[db_name]
            for col_name in target_collections:
                try:
                    col = db[col_name]
                    pipeline = [
                        {
                            "$match": {
                                "$or": [
                                    {"messages.content.text": {"$regex": r"(protocolo|chamado|ticket|wschamado|[0-9]{6,})", "$options": "i"}},
                                    {"status": {"$in": ["concluido", "finalizado", "closed"]}},
                                    {"context.active_flow": {"$exists": True}},
                                ]
                            }
                        },
                        {"$sort": {"updatedAt": -1, "_id": -1}},
                        {"$limit": limit},
                    ]
                    cursor = col.aggregate(pipeline)
                    for doc in cursor:
                        scenario = self._parse_mongo_doc_to_scenario(doc, db_name, col_name)
                        if scenario:
                            scenarios_found.append(scenario)
                except Exception as exc:
                    print(f"Erro ao agregar em {db_name}.{col_name}: {exc}")
                    continue

        return scenarios_found

    def _parse_mongo_doc_to_scenario(
        self, doc: dict[str, Any], db_name: str, col_name: str
    ) -> Scenario | None:
        """Converte um documento agregado do MongoDB em uma instância de Scenario."""
        ctx = doc.get("context") or {}
        active_flow = ctx.get("active_flow") or doc.get("active_flow") or "flow_indefinido"

        ui = ctx.get("user_info") or {}
        dados = ui.get("DADOS") if isinstance(ui, dict) else {}
        user_info = {
            "chapa": str(dados.get("CHAPA") or doc.get("userId") or ""),
            "nome": str(dados.get("NOME") or ""),
            "email": str(dados.get("EMAIL") or ""),
            "cpf": str(dados.get("CPF") or ""),
            "unidade": str(dados.get("UNIDADE") or "CAS"),
        }

        messages = doc.get("messages") or []
        turns: list[Turn] = []

        if isinstance(messages, list):
            for m in messages:
                if not isinstance(m, dict):
                    continue
                sender = m.get("sender")
                content = m.get("content") or {}
                text = content.get("text") if isinstance(content, dict) else str(content or "")
                if sender == "user" and text.strip():
                    turns.append(
                        Turn(
                            input_text=text.strip(),
                            description=f"Turno do usuário extraído do MongoDB ({db_name}.{col_name})",
                            expected=TurnExpected(active_flow=active_flow),
                        )
                    )

        if not turns:
            raw_input = doc.get("userInput")
            if raw_input:
                turns.append(
                    Turn(
                        input_text=str(raw_input).strip(),
                        description=f"Turno único extraído do MongoDB ({db_name}.{col_name})",
                        expected=TurnExpected(active_flow=active_flow),
                    )
                )

        if not turns:
            return None

        turns[-1].expected.is_done = True

        session_id = str(doc.get("sessionId") or doc.get("_id") or "sessao")
        return Scenario(
            id=f"mongo_{active_flow}_{session_id[:8]}",
            name=f"MongoDB - {active_flow.replace('_', ' ').title()}",
            flow_name=active_flow,
            metadata={
                "source": f"mongodb_{db_name}_{col_name}",
                "sessionId": session_id,
                "user_info": user_info,
            },
            turns=turns,
        )

    def build_dataset(
        self,
        theme_filter: str | None = None,
        include_canonical: bool = True,
    ) -> list[Scenario]:
        """Constrói o dataset mesclando MongoDB com o catálogo canônico."""
        mongo_connected = self.connect()
        mongo_scenarios: list[Scenario] = []

        if mongo_connected:
            print("🔍 Executando aggregation pipelines para extrair conversas de sucesso...")
            mongo_scenarios = self.aggregate_successful_conversations()
            print(f"📦 Total de conversas de sucesso extraídas do MongoDB: {len(mongo_scenarios)}")

        dataset: list[Scenario] = []

        dataset.extend(mongo_scenarios)

        if include_canonical:
            for can in CANONICAL_SCENARIOS:
                dataset.append(can)

        if theme_filter:
            tf = theme_filter.lower()
            dataset = [
                s for s in dataset
                if tf in s.flow_name.lower() or tf in s.id.lower() or tf in s.name.lower()
            ]

        seen_ids = set()
        deduped = []
        for s in dataset:
            if s.id not in seen_ids:
                seen_ids.add(s.id)
                deduped.append(s)

        return deduped


def print_summary_table(scenarios: list[Scenario]) -> None:
    print("\n" + "=" * 90)
    print(f"{'ID DO CENÁRIO':<38} | {'FLUXO':<28} | {'TURNOS':<6} | {'ORIGEM'}")
    print("-" * 90)
    for s in scenarios:
        origem = s.metadata.get("source", "manual")
        print(f"{s.id:<38} | {s.flow_name:<28} | {len(s.turns):<6} | {origem}")
    print("=" * 90)
    print(f"Total de cenários consolidados: {len(scenarios)}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agrega e gera dataset de testes a partir do MongoDB e catálogo corporativo"
    )
    parser.add_argument(
        "--export",
        metavar="JSON_FILE",
        default="tests/fixtures/real_test_scenarios.json",
        help="Caminho do arquivo JSON a ser gerado (default: tests/fixtures/real_test_scenarios.json)",
    )
    parser.add_argument(
        "--theme",
        metavar="TEMA",
        help="Filtra por tema (ex: gef, gep, cancelamento, nota_fiscal, etc.)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Exibe resumo do dataset consolidado",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    aggregator = MongoDatasetAggregator()
    scenarios = aggregator.build_dataset(theme_filter=args.theme)

    export_path = BASE_DIR / args.export
    save_scenarios_to_json(scenarios, export_path)
    print(f"💾 Dataset com {len(scenarios)} cenários salvo em: {export_path}")

    if args.summary or True:
        print_summary_table(scenarios)

    return 0


if __name__ == "__main__":
    sys.exit(main())
