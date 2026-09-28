from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

from core.config import SEARCH_VECTORY_INTERNAL_TOKEN, SEARCH_VECTORY_URL


class VectoryHttpError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Erro HTTP {status_code}: {detail}")


def _build_headers(*, accept: str = "application/json") -> dict[str, str]:
    headers = {
        "Accept": accept,
        "Content-Type": "application/json",
    }
    if SEARCH_VECTORY_INTERNAL_TOKEN:
        headers["X-Internal-Token"] = SEARCH_VECTORY_INTERNAL_TOKEN
    return headers


def post_json(
    path: str,
    payload: dict,
    *,
    base_url: str | None = None,
    timeout: float = 60.0,
) -> dict:
    root = (base_url or SEARCH_VECTORY_URL).rstrip("/")
    url = f"{root}/{path.lstrip('/')}"

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            json=payload,
            headers=_build_headers(),
        )

    if response.is_success:
        return response.json()

    detail = response.text.strip() or response.reason_phrase
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = str(body.get("detail") or body.get("error") or detail)
    except ValueError:
        pass

    if response.status_code == 401 and not SEARCH_VECTORY_INTERNAL_TOKEN:
        detail = (
            f"{detail} — defina SEARCH_VECTORY_INTERNAL_TOKEN no .env "
            "(mesmo INTERNAL_API_TOKEN do search-vectory) ou use URL local."
        )

    raise VectoryHttpError(response.status_code, detail)


def iter_ndjson(
    path: str,
    payload: dict,
    *,
    base_url: str | None = None,
    timeout: float = 120.0,
) -> Iterator[dict[str, Any]]:
    """POST streaming NDJSON; yield cada linha JSON."""
    root = (base_url or SEARCH_VECTORY_URL).rstrip("/")
    url = f"{root}/{path.lstrip('/')}"

    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            url,
            json=payload,
            headers=_build_headers(accept="application/x-ndjson"),
        ) as response:
            if not response.is_success:
                detail = response.read().decode("utf-8", errors="replace").strip()
                raise VectoryHttpError(response.status_code, detail or response.reason_phrase)
            for line in response.iter_lines():
                text = (line or "").strip()
                if not text:
                    continue
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
