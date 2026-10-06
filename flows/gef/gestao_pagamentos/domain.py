"""Abertura de chamado GEF — gestão de pagamentos."""

from __future__ import annotations

from typing import Any

FLOW_NAME = "gef_gestao_pagamentos"
SERVICE_LABEL = "a abertura de chamado de gestão de pagamentos"

ASK_TIPO = "Selecione o tipo de chamado de pagamento:"
ASK_TEXTO_METODO = "Descreva detalhadamente a sua solicitação."
ASK_DOCUMENTO = "Agora digite o número do CPF ou CNPJ:"
ASK_BANCO = "Por último, informe os dados bancários."
ASK_TEXTO = "Por favor, detalhe um pouco sobre seu problema."
ASK_ANEXO_METODO = "Deseja enviar algum arquivo?"
ASK_ANEXO = "Deseja incluir um anexo?"
ASK_ARQUIVO = "Anexe o arquivo desejado:"

TIPOS = [
    ("Método de pagamento", "metodo"),
    ("Recebimento não aparece", "recebimento"),
    ("CNPJ divergente", "cnpj"),
]

SIM_NAO = [
    ("Sim", "sim"),
    ("Não", "nao"),
]

_CLASSIFICACAO = {
    "metodo": "SNC_INT_002003003",
    "recebimento": "SNC-150106002",
    "cnpj": "SNC_INT_002003002",
}

_DESCRICAO = {
    "metodo": (
        "Gestão Orçamentária e Financeira, Contas a Pagar, "
        "Atualização do cadastro Fornecedor para Pessoa Jurídica e aluno devolução"
    ),
    "recebimento": (
        "Gestão Orçamentária e Financeira, Contas a Pagar, Recebimento não aparece"
    ),
    "cnpj": (
        "Gestão Orçamentária e Financeira, Contas a Pagar, Dúvidas sobre contas a pagar"
    ),
}

_CNPJ_TABLE = "Prestação de Contas - Terceiro (PJ ou PF)"


def classificacao_de(tipo_key: str) -> str:
    return _CLASSIFICACAO[tipo_key]


def descricao_de(tipo_key: str) -> str:
    return _DESCRICAO[tipo_key]


def pergunta_anexo(tipo_key: str) -> str:
    if tipo_key == "metodo":
        return ASK_ANEXO_METODO
    return ASK_ANEXO


def ticket_specs(tipo_key: str, flow_data: dict[str, Any]) -> list[dict[str, str]]:
    if tipo_key == "metodo":
        return [
            {"ASSETATTRID": "SNC_INT_00200300301", "ALNVALUE": "Pessoa Jurídica"},
            {
                "ASSETATTRID": "SNC_INT_00200300302",
                "ALNVALUE": str(flow_data.get("documento") or ""),
            },
            {
                "ASSETATTRID": "SNC_INT_00200300303",
                "ALNVALUE": "Alterar método de pagamento",
            },
            {
                "ASSETATTRID": "SNC_INT_00200300304",
                "ALNVALUE": str(flow_data.get("banco") or ""),
            },
        ]
    if tipo_key == "cnpj":
        return [
            {
                "ASSETATTRID": "SNC_INT_00200300201",
                "TABLEVALUE": _CNPJ_TABLE,
            }
        ]
    if tipo_key == "recebimento":
        return []
    raise ValueError(tipo_key)
