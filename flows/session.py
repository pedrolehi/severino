"""user_info da sessão. Os flows IBM leem isso e não pedem chapa, nome, e-mail, CPF nem unidade."""

from __future__ import annotations

from typing import Any


def _pick(sources: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text and text.lower() != "none":
                return text
    return ""


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "sim"}


def _acesso_relatorios(raw: dict[str, Any]) -> dict[str, Any] | None:
    acesso = raw.get("acessoRelatorios")
    if not isinstance(acesso, dict):
        dados = raw.get("DADOS")
        if isinstance(dados, dict):
            acesso = dados.get("acessoRelatorios")
    if not isinstance(acesso, dict):
        return None
    status = acesso.get("status")
    return {
        "status": "" if status is None else str(status).strip(),
        "acessoTotal": _flag(acesso.get("acessoTotal")),
    }


def normalize_user_info(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    dados = raw.get("DADOS")
    sources: list[dict[str, Any]] = []
    if isinstance(dados, dict):
        sources.append(dados)
    sources.append(raw)
    info: dict[str, Any] = {
        "chapa": _pick(sources, ("CHAPA", "chapa", "MATRICULA", "matricula")),
        "nome": _pick(sources, ("NOME", "nome")),
        "email": _pick(sources, ("EMAIL", "email")),
        "cpf": _pick(sources, ("CPF", "cpf")),
        "unidade": _pick(
            sources,
            ("UNIDADE", "SIGLA", "unidade", "sigla", "CODIGO_UNIDADE", "codigoUnidade"),
        ),
        "data_nascimento": _pick(
            sources,
            ("DATA_NASCIMENTO", "DATANASCIMENTO", "DTNASC", "dataNascimento"),
        ),
        "pis": _pick(sources, ("PIS", "PISPASEPNIT", "pisPasepNit", "pis")),
    }
    acesso = _acesso_relatorios(raw)
    if acesso:
        info["acessoRelatorios"] = acesso
    strings = [value for value in info.values() if isinstance(value, str)]
    if not any(strings) and not acesso:
        return None
    return info


def acesso_relatorios(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("user_info")
    if isinstance(raw, dict):
        found = raw.get("acessoRelatorios")
        if isinstance(found, dict):
            return {
                "status": str(found.get("status") or "").strip(),
                "acessoTotal": _flag(found.get("acessoTotal")),
            }
        parsed = _acesso_relatorios(raw)
        if parsed:
            return parsed
    return {"status": "", "acessoTotal": False}


def session_from_state(state: dict[str, Any]) -> dict[str, str]:
    raw = state.get("user_info")
    if isinstance(raw, dict) and "nome" in raw and "chapa" in raw:
        return {key: str(raw.get(key) or "") for key in (
            "chapa",
            "nome",
            "email",
            "cpf",
            "unidade",
            "data_nascimento",
            "pis",
        )}
    return normalize_user_info(raw if isinstance(raw, dict) else None) or {
        "chapa": "",
        "nome": "",
        "email": "",
        "cpf": "",
        "unidade": "",
        "data_nascimento": "",
        "pis": "",
    }


def missing_fields(info: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    labels = {
        "chapa": "chapa",
        "nome": "nome",
        "email": "e-mail",
        "cpf": "CPF",
        "unidade": "unidade",
    }
    return [labels.get(key, key) for key in keys if not str(info.get(key) or "").strip()]
