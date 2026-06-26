from __future__ import annotations

import httpx

from core.config import SEARCH_VECTORY_URL


class VectoryHttpError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Erro HTTP {status_code}: {detail}")


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
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
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

    raise VectoryHttpError(response.status_code, detail)
