"""Cliente HTTP fino para o senac-orchestrate."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True, slots=True)
class NotaFiscalResult:
    ok: bool
    links: list[str] = field(default_factory=list)
    status_code: int = 200
    error_detail: str | None = None
    not_found: bool = False


def _resolve_gef_payload(
    payload: dict[str, Any],
) -> tuple[int | None, dict[str, Any] | None, str | None]:
    """Normaliza body do orchestrate (flat GEF ou wrapper {status,data})."""
    # Flat: controller local retorna result.data → {CODIGO, DADOS, MENSAGEM}
    if "DADOS" in payload and "CODIGO" in payload:
        return 200, payload, None

    inner = payload.get("data")
    if isinstance(inner, dict) and "status" in inner:
        api = inner
    elif "status" in payload:
        api = payload
    else:
        return None, None, "Resposta inválida da API (formato inesperado)."

    status_http = api.get("status")
    error = api.get("error")
    if error:
        return status_http, None, str(error)

    gef = api.get("data")
    if isinstance(gef, dict) and "DADOS" in gef:
        return status_http, gef, None

    # Wrapper parcial: data já é o bloco GEF
    if isinstance(inner, dict) and "DADOS" in inner and "CODIGO" in inner:
        return status_http if status_http is not None else 200, inner, None

    return status_http, None, "Resposta inválida da API (formato inesperado)."


def _extract_links(payload: Any) -> tuple[int | None, list[str], str | None]:
    if not isinstance(payload, dict):
        return None, [], "Resposta inválida da API (formato inesperado)."

    status_http, gef, error = _resolve_gef_payload(payload)
    if error:
        return status_http, [], error
    if gef is None:
        return status_http, [], "Resposta inválida da API (formato inesperado)."

    codigo = gef.get("CODIGO")
    dados = gef.get("DADOS") or []
    if not isinstance(dados, list):
        dados = []

    links = [
        str(item["URL"]).strip()
        for item in dados
        if isinstance(item, dict) and item.get("URL")
    ]
    status_ok = status_http is None or status_http == 200
    ok = status_ok and (codigo == 200) and len(links) > 0
    if ok:
        return status_http or 200, links, None
    return status_http or 200, [], None


class OrchestrateClient:
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get_nota_fiscal(
        self,
        *,
        ano: str,
        mes: str,
        cnpj_senac: str,
        cnpj_cliente: str,
    ) -> NotaFiscalResult:
        url = f"{self._base_url}/gef/nota-fiscal"
        params = {
            "ano": ano,
            "mes": mes,
            "cnpj_senac": cnpj_senac,
            "cnpj_cliente": cnpj_cliente,
        }
        logger.info("orchestrate.get_nota_fiscal url=%s params=%s", url, params)

        try:
            response = httpx.get(url, params=params, timeout=self._timeout)
        except httpx.HTTPError as exc:
            logger.error("orchestrate transport_error: %s", exc)
            return NotaFiscalResult(
                ok=False,
                status_code=503,
                error_detail="serviço de integração temporariamente indisponível",
            )

        if response.status_code != 200:
            detail = response.text[:200] if response.text else response.reason_phrase
            return NotaFiscalResult(
                ok=False,
                status_code=response.status_code,
                error_detail=detail or f"erro HTTP {response.status_code}",
            )

        payload = response.json()
        status_http, links, error = _extract_links(payload)
        if error:
            return NotaFiscalResult(
                ok=False,
                status_code=status_http or 500,
                error_detail=error,
            )
        if not links:
            return NotaFiscalResult(
                ok=False,
                status_code=status_http or 200,
                not_found=True,
            )
        return NotaFiscalResult(ok=True, links=links, status_code=200)


class MockOrchestrateClient:
    def get_nota_fiscal(
        self,
        *,
        ano: str,
        mes: str,
        cnpj_senac: str,
        cnpj_cliente: str,
    ) -> NotaFiscalResult:
        digits = "".join(ch for ch in cnpj_cliente if ch.isdigit())
        if digits in {"00000000000000", "00000000000"}:
            return NotaFiscalResult(ok=False, status_code=200, not_found=True)
        return NotaFiscalResult(
            ok=True,
            links=[
                "https://nfe.prefeitura.sp.gov.br/contribuinte/notaprint.aspx?nf=123&verificacao=ABC"
            ],
        )


def create_orchestrate_client() -> OrchestrateClient | MockOrchestrateClient:
    use_mock = os.getenv("ORCHESTRATE_USE_MOCK", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    base_url = (os.getenv("SENAC_ORCHESTRATE_URL") or "").strip()
    if use_mock or not base_url:
        if not base_url:
            logger.warning(
                "SENAC_ORCHESTRATE_URL ausente — usando MockOrchestrateClient"
            )
        return MockOrchestrateClient()
    return OrchestrateClient(base_url)
