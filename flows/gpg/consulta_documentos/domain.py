"""Consulta de documentos GPG."""

from __future__ import annotations

FLOW_NAME = "consulta_documentos"
SERVICE_LABEL = "a consulta de documentos"
NEXT = [
    ("Buscar de novo", "de_novo"),
    ("Encerrar", "encerrar"),
]
