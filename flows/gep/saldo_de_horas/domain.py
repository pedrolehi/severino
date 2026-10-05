"""Saldo de horas GEP. Texto igual ao bloco Monta mensagem do Flow_GEP_Saldo_de_horas."""

from __future__ import annotations

import datetime
from typing import Any

FLOW_NAME = "saldo_de_horas"
SERVICE_LABEL = "o saldo de horas"

MESES_EXTENSO = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _mes_extenso(numero_mes: int) -> str:
    return MESES_EXTENSO.get(numero_mes, "")


def _colorir_se_negativo(valor: str) -> str:
    texto = str(valor).strip()
    if texto.startswith("-"):
        return f'<span style="color: red;">{texto}</span>'
    return texto


def _extrair_valores(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "0:00", "0:00"
    anterior = payload.get("saldo_anterior") or payload.get("Saldo Anterior")
    atual = payload.get("saldo_atual") or payload.get("Saldo Atual")
    if not anterior and not atual and isinstance(payload.get("data"), dict):
        return _extrair_valores(payload["data"])
    if not anterior:
        anterior = "0:00"
    if not atual:
        atual = "0:00"
    return str(anterior), str(atual)


def meses_referencia(today: datetime.date | None = None) -> tuple[str, str]:
    """Prévia = mês anterior ao atual. Fechado = mês anterior à prévia."""
    base = today or datetime.date.today()
    mes_previa = 12 if base.month == 1 else base.month - 1
    mes_fechado = 12 if mes_previa == 1 else mes_previa - 1
    return _mes_extenso(mes_previa), _mes_extenso(mes_fechado)


def format_saldo_message(payload: Any, today: datetime.date | None = None) -> str:
    mes_atual_extenso, mes_anterior_extenso = meses_referencia(today)
    saldo_anterior, saldo_atual = _extrair_valores(payload)
    saldo_anterior_formatado = _colorir_se_negativo(saldo_anterior)
    saldo_atual_formatado = _colorir_se_negativo(saldo_atual)
    return (
        f"Saldo do **banco de horas** até {mes_anterior_extenso} (mês fechado): "
        f"**{saldo_anterior_formatado}**\n\n"
        f"Prévia do **banco de horas** do mês de {mes_atual_extenso}: "
        f"**{saldo_atual_formatado}**\n\n"
        '> <span style="color: red;">**Atenção:**</span> O saldo de banco de horas '
        "é referente ao ponto do _mês fechado_ e poderá ser ajustado conforme "
        "correções solicitadas pelo setor administrativo.\n"
    )
