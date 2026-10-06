"""Centro de custo GEF."""

from __future__ import annotations

FLOW_NAME = "centro_de_custo"
SERVICE_LABEL = "a consulta de centro de custo"
NEXT = [
    ("Nova consulta", "de_novo"),
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
