"""Leitura de listas e montagem de payload dos chamados."""

from __future__ import annotations

import re
from typing import Any


def _plain(text: str) -> str:
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", text)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def option_pairs(payload: Any) -> list[tuple[str, str]]:
    if not isinstance(payload, dict):
        return []
    options = payload.get("options")
    if isinstance(options, list) and options:
        pairs = [
            (str(item["label"]), str(item["value"]))
            for item in options
            if isinstance(item, dict) and item.get("label") and item.get("value")
        ]
        if pairs:
            return pairs
    listing = payload.get("list")
    if isinstance(listing, list) and listing:
        pairs = []
        for item in listing:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                pairs.append((_plain(str(item[0])) or str(item[1]), str(item[1])))
        if pairs:
            return pairs
    dados = payload.get("DADOS")
    if isinstance(dados, list):
        pairs = []
        for item in dados:
            if isinstance(item, dict) and item.get("caixa"):
                label = (
                    f"{item.get('descrCaixa') or item['caixa']}"
                    f" - registradora {item.get('registradora') or ''}"
                ).strip()
                pairs.append((label, str(item["caixa"])))
        if pairs:
            return pairs
    for key in ("data",):
        nested = payload.get(key)
        if isinstance(nested, dict):
            found = option_pairs(nested)
            if found:
                return found
    return []


def documentos_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "Nenhum documento encontrado."
    bloco = payload.get("resultDocumentos")
    if isinstance(bloco, dict):
        raw = str(bloco.get("strDocumentos") or "")
        return _plain(raw) or "Nenhum documento encontrado."
    if isinstance(payload.get("data"), dict):
        return documentos_text(payload["data"])
    return "Nenhum documento encontrado."


def anexo_texto(data: dict[str, Any], key: str = "anexo") -> str:
    value = data.get(key)
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("file_url") or value.get("url") or "").strip()
    return ""


def pessoa_body(info: dict[str, str], *, tipo: str, classification: str, texto: str, tema: str, subtema: str = "") -> dict[str, str]:
    return {
        "nome": info.get("nome") or "",
        "email": info.get("email") or "",
        "cpf": info.get("cpf") or "",
        "unidade": info.get("unidade") or "",
        "tipo_chamado": tipo,
        "classificationId": classification,
        "classStructureId": "",
        "commodity": "",
        "commodityGroup": "",
        "texto": texto,
        "tema": tema,
        "subtema": subtema,
        "dataNascimento": info.get("data_nascimento") or "",
        "pisPasepNit": info.get("pis") or "",
        "anexo": "",
    }


def geral_body(
    info: dict[str, str],
    *,
    tipo: str,
    classification: str,
    texto: str,
    area: str | None = None,
) -> dict[str, str]:
    nome = info.get("nome") or ""
    email = info.get("email") or ""
    body = {
        "nome": nome,
        "email": email,
        "cpf": info.get("cpf") or "",
        "unidade": info.get("unidade") or "",
        "tipo_chamado": tipo,
        "classificationId": classification,
        "CLASSIFICATIONID": classification,
        "DESCRIPTION": tipo,
        "DESCRIPTION_LONGDESCRIPTION": texto,
        "AFFECTEDPERSON": nome,
        "REPORTEDBY": nome,
        "REPORTEDEMAIL": email,
        "AFFECTEDEMAIL": email,
        "LOCATION": info.get("unidade") or "",
        "texto": texto,
    }
    if area:
        body["area"] = area
    return body
