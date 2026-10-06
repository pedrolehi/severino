"""Abertura de chamado GEF — gestão de pagamentos."""

from __future__ import annotations

FLOW_NAME = "gef_gestao_pagamentos"
SERVICE_LABEL = "a abertura de chamado de gestão de pagamentos"

GESTAO = [
    ("Método de pagamento", "SNC_INT_002003003"),
    ("Recebimento não aparece", "SNC-15003001"),
    ("CNPJ divergente", "SNC_INT_002003002"),
]
