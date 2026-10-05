"""Abertura de chamado GEF."""

from __future__ import annotations

FLOW_NAME = "gef_abertura_chamado"
SERVICE_LABEL = "a abertura de chamado da GEF"
CLASSIFICACAO_CANCELAMENTO = "SNC_INT_00200601"
CLASSIFICACAO_RELATORIOS = "SNC_INT_00500203"

ASSUNTOS = [
    ("Gestão de pagamentos", "gestao"),
    ("Relatórios orçamentários", "relatorios"),
    ("Cancelamento de matrícula", "cancelamento"),
]

GESTAO = [
    ("Método de pagamento", "SNC_INT_002003003"),
    ("Recebimento não aparece", "SNC-15003001"),
    ("CNPJ divergente", "SNC_INT_002003002"),
]
