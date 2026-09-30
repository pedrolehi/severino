"""Cliente HTTP OpenJEV — POST /v1/systemone."""

from __future__ import annotations

from typing import Any

import httpx

from core.config import (
    OPENJEV_API_KEY,
    OPENJEV_BASE_URL,
    OPENJEV_MODEL,
    OPENJEV_TIMEOUT_S,
)


class JevClientError(RuntimeError):
    """Falha HTTP ou payload invalido do OpenJEV."""


_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            timeout=OPENJEV_TIMEOUT_S,
            limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
        )
    return _http_client


def build_systemone_url(base_url: str | None = None) -> str:
    base = (base_url or OPENJEV_BASE_URL).rstrip("/")
    return f"{base}/v1/systemone"


def call_systemone(
    *,
    state: Any,
    questions: dict[str, Any],
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """POST /v1/systemone. Retorna body JSON com `answers`."""
    if not questions:
        raise JevClientError("questions vazio")

    url = build_systemone_url(base_url)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = OPENJEV_API_KEY if api_key is None else api_key
    if key:
        headers["Authorization"] = f"Bearer {key}"

    payload = {
        "model": model or OPENJEV_MODEL,
        "state": state,
        "questions": questions,
    }
    timeout = OPENJEV_TIMEOUT_S if timeout_s is None else timeout_s

    try:
        response = _get_http_client().post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except httpx.RequestError as exc:
        raise JevClientError(f"rede: {exc}") from exc

    if response.status_code >= 400:
        detail = (response.text or "")[:500]
        raise JevClientError(f"HTTP {response.status_code}: {detail}")

    try:
        body = response.json()
    except ValueError as exc:
        raise JevClientError("resposta nao-JSON") from exc

    if not isinstance(body, dict):
        raise JevClientError("body invalido")
    return body
