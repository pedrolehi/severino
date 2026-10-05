"""Abertura de chamado GEP. Filhos: crachás, ponto, benefícios, carta convite."""

from __future__ import annotations

FLOW_NAME = "gep_abertura_chamado"
SERVICE_LABEL = "a abertura de chamado da GEP"

ASSUNTOS = [
    ("Crachás", "crachas"),
    ("Ponto eletrônico", "ponto"),
    ("Benefícios", "beneficios"),
    ("Carta convite", "carta"),
]

CARTA = [
    ("Consulta jurídica", "consulta"),
    ("Dúvidas gerais", "duvidas"),
    ("Ajustes de dados cadastrais", "ajustes"),
]

TIPOS = {
    "crachas": ("Crachás", "SNC_INT_00300702"),
    "ponto": ("Ponto eletrônico", "SNC-15003001"),
    "beneficios": ("Benefícios", "SNC_INT_003012001"),
    "consulta": ("Consulta juridica", "SNC_INT_00301001"),
    "duvidas": ("Dúvidas gerais", "SNC_INT_003011"),
    "ajustes": ("Ajustes de dados cadastrais", "SNC_INT_00300701"),
}

ASK_ANEXO = [
    ("Sim", "sim"),
    ("Não", "nao"),
]
