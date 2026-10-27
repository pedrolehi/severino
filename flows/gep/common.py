"""Componentes e rotinas reutilizáveis para fluxos de abertura de chamado da GEP."""

from __future__ import annotations

from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import protocol_message
from flows.payload import pessoa_body
from flows.session import missing_fields

ASK_ANEXO = [
    ("Sim", "sim"),
    ("Não", "nao"),
]

# Unidade do colaborador não é exigida nem enviada nos chamados GEP: a sessão real não a traz.
SESSION_KEYS = ("nome", "email", "cpf")


def checar_sessao_gep(info: dict[str, str]) -> tuple[str, ...]:
    return missing_fields(info, SESSION_KEYS)


def anexo_form(
    *,
    name: str,
    title: str = "Anexo",
    field_title: str = "Selecione o arquivo desejado:",
    max_size_mb: int = 10,
) -> dict[str, Any]:
    return {
        "component": "form",
        "name": name,
        "title": title,
        "fields": [
            {
                "key": "anexo",
                "title": field_title,
                "widget": "file",
                "required": True,
                "maxSizeMb": max_size_mb,
            }
        ],
    }


def submeter_chamado_gep(
    info: dict[str, str],
    *,
    tipo: str,
    classification: str,
    texto: str,
    tema: str,
    subtema: str = "",
    anexo: str = "",
    description: str | None = None,
    ticketspecs: list[dict[str, Any]] | None = None,
) -> str:
    body = pessoa_body(
        {**info, "unidade": ""},
        tipo=tipo,
        classification=classification,
        texto=texto,
        tema=tema,
        subtema=subtema,
        description=description,
        ticketspecs=ticketspecs,
    )
    if anexo:
        body["anexo"] = anexo

    result = create_orchestrate_client().open_ticket(body)
    if result.ticket_id:
        return protocol_message(result.ticket_id, None)
    return protocol_message(None, result.error_detail)
