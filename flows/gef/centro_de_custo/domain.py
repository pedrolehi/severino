"""Centro de custo GEF."""

from __future__ import annotations

FLOW_NAME = "centro_de_custo"
SERVICE_LABEL = "o serviço de centro de custo"

MENU_INICIAL = [
    ("Consultar Centro de Custo", "consultar"),
    ("Solicitar Abertura de Centro de Custo", "solicitar"),
]

MSG_SOLICITAR_ABERTURA = (
    "Para solicitar abertura do centro de custo, acesse o link: \n"
    "[Serviços Financeiros (senac.br)](https://www.intranet.sp.senac.br/intranet-frontend/sistemas-integrados/detalhes/459)"
)

CURSO_NAO_ENCONTRADO = {"não encontrei o curso", "curso não encontrado"}

NEXT = [
    ("Visualizar outro centro de custo", "de_novo"),
    ("Encerrar", "encerrar"),
]

_FICHA_LABELS = (
    "Centro de custo",
    "Ficha Técnica",
    "Título do Serviço",
    "Subárea",
    "Modalidade",
    "Origem",
)


def format_ficha(raw: str) -> str:
    """HTML da ficha vira lista markdown. Select continua com o texto puro."""
    lines: list[str] = []
    for line in (raw or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        label, sep, value = cleaned.partition(":")
        name = label.strip()
        if sep and name in _FICHA_LABELS:
            lines.append(f"- **{name}:** {value.strip()}")
            continue
        lines.append(cleaned)
    return "\n".join(lines)
