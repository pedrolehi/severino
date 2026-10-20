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


# Tabela de descrições oficiais do Catálogo de Serviços do Senac (alinhada ao IBM Control Desk / Maximo)
GEP_FIXED_DESCRIPTIONS: dict[str, str] = {
    "Crachás": "Gestão de Pessoas,Administração de Pessoal,Esclarecimento sobre emissão de crachás",
    "Ponto eletrônico": "Gestão da Tecnologia,Suporte para Sistemas,Relatar um erro,Relatar um erro",
    "Ajustes de dados cadastrais": "Gestão de pessoas, Administração de Pessoal, Ajuste de dados no Rhevolution para Pessoa Física",
    "Alteração de dados cadastrais/bancários - PF": "Gestão de pessoas, Administração de Pessoal, Ajuste de dados no Rhevolution para Pessoa Física",
    "Ajuste de dados bancários": "Ajuste de dados no Rhevolution para Pessoa Física",
    "Consulta Juridica": "Gestão de Pessoas,Consulta Jurídica,Consulta jurídica para contratações de prestadores de serviço carta convite - Pessoa Física/Jurídica",
    "Consulta juridica": "Gestão de Pessoas,Consulta Jurídica,Consulta jurídica para contratações de prestadores de serviço carta convite - Pessoa Física/Jurídica",
    "Dúvidas gerais": "Gestão de pessoas,Dúvidas sobre prestadores de serviço carta convite PF e PJ",
    "RPA - Consulta PF": "Gestão da Tecnologia,Suporte para Sistemas,Relatar um erro,Relatar um erro",
    "Problemas ou indisponibilidade do robô": "Gestão da Tecnologia,Suporte para Sistemas,Relatar um erro,Relatar um erro",
}

def resolve_fixed_description(tipo: str, *, tema: str = "", subtema: str = "") -> str:
    """Resolve a DESCRIPTION hierárquica exata do Catálogo de Serviços do Maximo."""
    if tipo == "Benefícios Cooperativa" or (tipo == "Benefícios" and subtema):
        return (
            "Gestão de Pessoas,Assist. Médica / Auxílio Educ. Infantil / Presente casamento / "
            f"Cooperativa / Consignado Santander,Esclareça suas dúvidas sobre estes temas,Cooperativa,{subtema}"
        )
    if tipo == "Benefícios":
        return (
            "Gestão de Pessoas,Assist. Médica / Auxílio Educ. Infantil / Presente casamento / "
            f"Cooperativa / Consignado Santander,Esclareça suas dúvidas sobre estes temas,{tema}"
        )
    if tipo in GEP_FIXED_DESCRIPTIONS:
        return GEP_FIXED_DESCRIPTIONS[tipo]
    return f"Gestão de Pessoas - {tipo}"


def resolve_gep_ticket_specs(
    tipo: str,
    info: dict[str, str],
    *,
    tema: str = "",
    subtema: str = "",
) -> list[dict[str, str]]:
    """Gera a lista de TICKETSPECS estruturada de acordo com o padrão do Maximo."""
    if tipo in ("Crachás", "Ponto eletrônico"):
        return []
    if tipo in ("Benefícios", "Benefícios Cooperativa"):
        return [
            {"ASSETATTRID": "SNC_INT_003012001001", "ALNVALUE": tema},
            {"ASSETATTRID": "SNC_INT_003012001002", "ALNVALUE": subtema},
            {"ASSETATTRID": "SNC_INT_003012001003", "ALNVALUE": info.get("cpf") or ""},
        ]
    if tipo in ("Consulta Juridica", "Consulta juridica"):
        return [
            {"ASSETATTRID": "SNC_INT_0030100101", "ALNVALUE": info.get("nome") or ""},
            {"ASSETATTRID": "SNC_INT_0030100102", "ALNVALUE": info.get("cpf") or ""},
            {"ASSETATTRID": "SNC_INT_0030100103", "ALNVALUE": info.get("data_nascimento") or ""},
            {"ASSETATTRID": "SNC_INT_0030100104", "ALNVALUE": info.get("pis") or ""},
        ]
    if tipo == "Dúvidas gerais":
        return [{"ASSETATTRID": "SNC_INT_0030060101", "ALNVALUE": tema}]
    if tipo == "RPA - Consulta PF":
        return [{"ASSETATTRID": "SNC-150142001001", "ALNVALUE": ""}]
    return []


def pessoa_body(
    info: dict[str, str],
    *,
    tipo: str,
    classification: str,
    texto: str,
    tema: str,
    subtema: str = "",
    description: str | None = None,
    ticketspecs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    nome = info.get("nome") or ""
    email = info.get("email") or ""
    unidade = info.get("unidade") or ""
    long_desc = f"Nome: {nome}\nEmail: {email}\nUnidade: {unidade}\nTema: {tema}"
    if subtema:
        long_desc += f" | Subtema: {subtema}"
    long_desc += f"\nDescrição: {texto}"

    final_desc = description or resolve_fixed_description(tipo, tema=tema, subtema=subtema)
    final_specs = (
        ticketspecs
        if ticketspecs is not None
        else resolve_gep_ticket_specs(tipo, info, tema=tema, subtema=subtema)
    )

    body = {
        "area": "gep",
        "nome": nome,
        "email": email,
        "cpf": info.get("cpf") or "",
        "unidade": unidade,
        "tipo_chamado": tipo,
        "classificationId": classification,
        "CLASSIFICATIONID": classification,
        "texto": texto,
        "tema": tema,
        "subtema": subtema,
        "REPORTEDBY": nome,
        "AFFECTEDPERSON": nome,
        "REPORTEDEMAIL": email,
        "AFFECTEDEMAIL": email,
        "LOCATION": unidade,
        "UNIDADE_CURSO": unidade,
        "DESCRIPTION": final_desc,
        "DESCRIPTION_LONGDESCRIPTION": long_desc,
        "dataNascimento": info.get("data_nascimento") or "",
        "pisPasepNit": info.get("pis") or "",
        "anexo": "",
    }
    if final_specs:
        body["TICKETSPECS"] = final_specs
    return body


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
