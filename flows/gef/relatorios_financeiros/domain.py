"""Relatórios financeiros GEF. Textos e regras do Flow_GEF_R_F."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

FLOW_NAME = "relatorios_financeiros"
SERVICE_LABEL = "os relatórios financeiros"
CONFIRM = [
    ("Sim", "sim"),
    ("Não", "nao"),
]

UNAVAILABLE = (
    "Os relatórios financeiros estão temporariamente indisponíveis. "
    "Por favor, tente novamente mais tarde."
)
NO_ACCESS = "Você não tem acesso aos relatórios financeiros."
LISTA = (
    "Perfeito, os relatórios gerados são:\n\n"
    "- Anulação de recibo\n"
    "- Cancelamentos\n"
    "- Conciliação de caixa\n"
    "- Desconto\n"
    "- Isenção\n"
    "- Matrícula por data\n"
    "- Não processados\n"
    "- Prorrogação de encargos\n"
    "- Reversão de encargos\n"
    "- Reversão de pagamentos\n"
    "- Transações pix\n\n"
    "Os relatórios “Matrícula por data”, “Não processados” e "
    "“Prorrogação de encargos” não fazem parte do movimento financeiro diário, "
    "porém serão enviados para acompanhamento da unidade."
)
AVISO = (
    "O relatório de Dados e Status de Estudantes deverá ser emitido pela unidade "
    "em caso de oferta cancelada pelo Senac."
)
ASK_EMITIR = "Deseja emitir os relatórios?"
ASK_DATA = "Selecione a data"
ASK_DATA_FIM = (
    "Agora selecione a data final do período que deseja emitir os relatórios. "
    "Lembrando que ela sempre deve ser anterior a data de hoje!"
)
ASK_CONFIRM_DATA = "Posso confirmar a data acima?"
ASK_CONFIRM_PERIODO = "Posso confirmar?"
ASK_CAIXA = "Agora escolha o caixa:"
ASK_CONFIRM_CAIXA = "Você confirma a seleção?"
EMPTY_CAIXAS = "Nenhum caixa disponível para seleção."
GENERATING = "Os relatórios estão sendo gerados!\n\nEm breve você receberá por e-mail."
ASK_OUTRA = "Deseja gerar relatórios com outra data?"
THANKS = "Ok, obrigado por sua visita!"
MORE_HELP = "Precisa de ajuda em algo mais?"

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


def acesso_status_ok(acesso: dict[str, Any]) -> bool:
    return str(acesso.get("status") or "") == "200"


def acesso_total(acesso: dict[str, Any]) -> bool:
    return acesso.get("acessoTotal") is True


def parse_date(value: str) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def needs_end_date(day: date) -> bool:
    return day.weekday() in (5, 6)


def show_date(day: date) -> str:
    return day.strftime("%d-%m-%Y")


def api_date(day: date) -> str:
    return day.isoformat()


def before_today(day: date, today: date | None = None) -> bool:
    return day < (today or date.today())


def periodo_text(inicio: date, fim: date) -> str:
    return (
        "Vi que você solicitou os relatórios de "
        f"**{show_date(inicio)}** até **{show_date(fim)}**."
    )


def _walk_dados(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    for path in (
        ("data", "data", "data", "DADOS"),
        ("data", "data", "DADOS"),
        ("data", "DADOS"),
        ("DADOS",),
    ):
        cur: Any = payload
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if isinstance(cur, list):
            return cur
    return []


def _sem_prefixo_caixa(texto: str) -> str:
    if texto.lower().startswith("caixa "):
        return texto[6:].strip()
    return texto


def caixa_pairs(payload: Any) -> list[tuple[str, str]]:
    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for item in _walk_dados(payload):
        if not isinstance(item, dict):
            continue
        caixa = str(item.get("caixa") or "").strip()
        registradora = str(item.get("registradora") or "").strip()
        if not caixa or not registradora:
            continue
        value = f"{caixa}|{registradora}"
        if value in seen:
            continue
        seen.add(value)
        descr = _sem_prefixo_caixa(str(item.get("descrCaixa") or f"Caixa {caixa}").strip())
        pairs.append((descr or caixa, value))
    return pairs


def caixa_code(value: str) -> str:
    return str(value or "").split("|", 1)[0].strip()
