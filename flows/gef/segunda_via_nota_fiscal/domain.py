"""Domínio do flow segunda via de nota fiscal (miolo da tool + UX).

Textos alinhados a Flow_GEF_Segunda_via_nota_fiscal.json (senac-multiagent).
"""

from __future__ import annotations

import json
import re
from typing import Any

UNIDADES_CNPJ_SENAC: dict[str, str] = {
    "ACL": "03.709.814/0073-62",
    "ANA": "03.709.814/0010-89",
    "BRA": "03.709.814/0089-20",
    "CAS": "03.709.814/0064-71",
    "CEC": "03.709.814/0017-55",
    "FAU": "03.709.814/0053-19",
    "FCO": "03.709.814/0006-00",
    "GEF": "03.709.814/0001-98",
    "ITQ": "03.709.814/0016-74",
    "JBQ": "03.709.814/0003-50",
    "L13": "03.709.814/0055-80",
    "MAI": "03.709.814/0005-11",
    "PEN": "03.709.814/0007-83",
    "PRI": "03.709.814/0074-43",
    "SCI": "03.709.814/0054-08",
    "SMP": "03.709.814/0086-87",
    "TAT": "03.709.814/0008-64",
    "TIR": "03.709.814/0045-09",
    "TIT": "03.709.814/0002-79",
    "VPR": "03.709.814/0009-45",
}

CHAMADO_FORA_SP_URL = (
    "https://catalogo.sp.senac.br/home/segment/item/3J6cozIjGiYJ/"
)

# Coleta: título + helps do form ColetaDados (CLI sem widget)
COLLECT_HINT = (
    "Solicitação de segunda via de nota fiscal\n\n"
    "CNPJ da Unidade:\n"
    "Informe o CNPJ da unidade do município de São Paulo "
    "ou a sigla da unidade na capital.\n"
    "Ex.: 00.000.000/0000-00\n"
    f"Siglas: {', '.join(sorted(UNIDADES_CNPJ_SENAC.keys()))}\n\n"
    "CNPJ ou CPF do responsável financeiro:\n"
    "Informe o CNPJ ou CPF do responsável financeiro (tomador de serviço)\n"
    "Ex. CNPJ: 00.000.000/0000-00 Ex. CPF : 000.000.000-00\n\n"
    "Insira uma data (competência fiscal):\n"
    "Informe a competência fiscal.\n\n"
    "Responda em uma linha, separados por vírgula:\n"
    "`<sigla ou CNPJ da unidade>, <CNPJ/CPF do tomador>, <mm/aaaa>`\n"
    "Exemplo: `GEF, 12.345.678/0001-90, 03/2024`"
)

COLLECT_MES_HINT = (
    "Informe a nova competência (mês e ano):\n"
    "Insira uma data — informe a competência fiscal.\n"
    "Exemplo: `03/2024` ou `2024-03`"
)


def parse_boolean(text: str) -> bool | None:
    normalized = text.strip().lower()
    if normalized in {"sim", "s", "true", "yes", "1"}:
        return True
    if normalized in {"não", "nao", "n", "false", "no", "0"}:
        return False
    return None


def normalize_mes_ano(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if "-" in s:
        parts = s.split("-")
        if len(parts) >= 2 and len(parts[0]) == 4 and parts[1].isdigit():
            return f"{parts[0]}-{parts[1].zfill(2)}"
    if "/" in s:
        a, b = s.split("/", 1)
        a, b = a.strip(), b.strip()
        if len(b) == 4 and a.isdigit() and b.isdigit():
            return f"{b}-{a.zfill(2)}"
        if len(a) == 4 and a.isdigit() and b.isdigit():
            return f"{a}-{b.zfill(2)}"
    return None


def parse_mes_ano_input(text: str) -> str | None:
    raw = (text or "").strip()
    data = form_data_of(raw)
    if data:
        value = _first_value(data, "mes_ano", "Competência")
        if value and parse_mes_ano(value):
            return value
        return None
    if parse_mes_ano(raw):
        return raw
    return None


def parse_mes_ano(mes_ano: str) -> tuple[str, str] | None:
    normalized = normalize_mes_ano(mes_ano)
    if not normalized or "-" not in normalized:
        return None
    ano, mes = normalized.split("-", 1)
    if len(ano) == 4 and mes.isdigit() and 1 <= int(mes) <= 12:
        return ano, mes.zfill(2)
    return None


def to_mes_ano_exibicao(value: str | None) -> str | None:
    tool = normalize_mes_ano(value)
    if not tool or "-" not in tool:
        return value
    yyyy, mm = tool.split("-", 1)
    return f"{mm.zfill(2)}/{yyyy}"


def resolve_cnpj_senac(value: str | None) -> str | None:
    if not value:
        return None
    sigla = str(value).strip().upper()
    if sigla in UNIDADES_CNPJ_SENAC:
        return UNIDADES_CNPJ_SENAC[sigla]
    return str(value).strip()


def parse_form_body(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw.startswith("{"):
        return None
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("form_data"), dict):
        return None
    return body


def form_data_of(text: str) -> dict[str, Any]:
    body = parse_form_body(text)
    if body is None:
        return {}
    data = body.get("form_data")
    return data if isinstance(data, dict) else {}


def is_form_cancel(text: str) -> bool:
    body = parse_form_body(text)
    return bool(body and body.get("form_operation") == "cancel")


def _first_value(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def parse_coleta_text(text: str) -> dict[str, str] | None:
    raw = (text or "").strip()
    if not raw:
        return None

    data = form_data_of(raw)
    if data:
        slots = {
            "cnpj_senac": _first_value(data, "cnpj_senac", "CNPJ da Unidade"),
            "cnpj_cliente": _first_value(
                data,
                "cnpj_cliente",
                "CNPJ ou CPF do responsável financeiro",
            ),
            "mes_ano": _first_value(data, "mes_ano", "Competência"),
        }
        if slots["cnpj_senac"] and slots["cnpj_cliente"] and slots["mes_ano"]:
            return slots
        return None

    parts = re.split(r"[,|;]", raw)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) != 3:
        return None

    return {
        "cnpj_senac": parts[0],
        "cnpj_cliente": parts[1],
        "mes_ano": parts[2],
    }


def validate_coleta(slots: dict[str, str]) -> str | None:
    if not slots.get("cnpj_senac"):
        return "Informe o CNPJ da unidade ou a sigla."
    if not slots.get("cnpj_cliente"):
        return "Informe o CNPJ ou CPF do responsável financeiro."
    if not slots.get("mes_ano"):
        return "Informe a competência (mês e ano)."
    if not parse_mes_ano(slots["mes_ano"]):
        return "Competência inválida. Use mm/aaaa ou yyyy-mm."
    return None


def ask_sp_message() -> str:
    # display_name original: "Deseja emitir a 2a via..."
    return "Deseja emitir a 2a via da nota fiscal do município de São Paulo?"


def fora_sp_message() -> str:
    return (
        "Desculpe, estamos somente atendendo as solicitações para o "
        "município de São Paulo.\n\n"
        "Caso deseje, você pode fazer a abertura de um chamado "
        f'<a href="{CHAMADO_FORA_SP_URL}" target="_blank">clicando aqui</a>.'
    )


def ask_nova_competencia_message() -> str:
    return "Quer outra competência para este mesmo cliente?"


def ask_outro_prestador_message() -> str:
    return "Quer a nota de outro responsável financeiro?"


def ask_retry_question() -> str:
    return "Quer tentar de novo?"


def build_not_found_message(mes_ano_exibicao: str | None) -> str:
    competencia = mes_ano_exibicao or "informada"
    return (
        f"Não encontrei nota fiscal para a competência {competencia}.\n\n"
        "A prefeitura não devolveu link com a unidade, o responsável financeiro "
        "e o mês informados.\n\n"
        "Confira se a competência está em mês/ano e se o CNPJ é o da unidade de São Paulo."
    )


def ask_retry_message(competencia: str | None) -> str:
    return (
        f"{build_not_found_message(competencia)}\n\n{ask_retry_question()}"
    )


def build_success_message(links: list[str], competencia: str | None = None) -> str:
    comp = competencia or "informada"
    quantidade = len(links)
    if quantidade == 1:
        abertura = f"Encontrei a nota da competência {comp}."
        meio = "Este link abre a segunda via no site da Prefeitura de São Paulo:"
    else:
        abertura = f"Encontrei {quantidade} notas da competência {comp}."
        meio = "Cada link abre uma segunda via no site da Prefeitura de São Paulo:"
    links_text = "\n\n".join(links)
    return (
        f"{abertura}\n\n"
        f"{meio}\n\n"
        f"{links_text}\n\n"
        "Antes de encaminhar ao cliente, confira os dados da nota "
        "no relatório CODEPE do Senac Solution."
    )


def build_api_error_message(detail: str) -> str:
    motivo = detail.strip() or "o serviço não respondeu"
    return (
        "Não consegui consultar a nota fiscal agora.\n\n"
        f"{motivo[:1].upper()}{motivo[1:].rstrip('.')}.\n\n"
        "Nada foi emitido. Dá para repetir a busca ou ajustar "
        "a competência, o CNPJ da unidade ou o documento do responsável."
    )


def something_else_message() -> str:
    return "Precisa de ajuda em algo mais?"


def build_collect_prompt(*, error: str | None = None) -> str:
    prefix = f"{error}\n\n" if error else ""
    return f"{prefix}{COLLECT_HINT}"


def build_collect_mes_prompt(*, error: str | None = None) -> str:
    prefix = f"{error}\n\n" if error else ""
    return f"{prefix}{COLLECT_MES_HINT}"


def last_user_text(messages: list[Any]) -> str:
    from langchain_core.messages import HumanMessage

    for message in reversed(messages or []):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""
