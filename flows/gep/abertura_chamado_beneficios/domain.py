"""Domínio — abertura de chamado de benefícios GEP.

Reproduz fielmente as opções do Flow_GEP_abertura_chamado_beneficios do Watson Orchestrate.
"""

from __future__ import annotations

FLOW_NAME = "gep_abertura_chamado_beneficios"
SERVICE_LABEL = "a abertura de chamado de benefícios"
CLASSIFICATION_ID = "SNC_INT_003012001"
TIPO_CHAMADO = "Benefícios"

TEMAS = [
    ("Assistência Médica", "Assistência Médica"),
    ("Auxílio Educação Infantil", "Auxílio Educação Infantil"),
    ("Consignado Santander", "Consignado Santander"),
    ("Cooperativa", "Cooperativa"),
    ("Presente de Casamento", "Presente de Casamento"),
]

TEMAS_COOPERATIVA = [
    ("Auxílio", "Auxílio"),
    ("Cadastro", "Cadastro"),
    ("Consignado", "Consignado"),
    ("Desligamento", "Desligamento"),
    ("Reembolso", "Reembolso"),
]
