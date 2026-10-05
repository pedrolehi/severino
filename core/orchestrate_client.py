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
class CallResult:
    ok: bool
    payload: Any = None
    status_code: int = 200
    error_detail: str | None = None
    ticket_id: str | None = None


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

    def _call(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> CallResult:
        url = f"{self._base_url}{path}"
        logger.info("orchestrate.%s %s", method, url)
        try:
            response = httpx.request(
                method,
                url,
                params=params,
                json=body,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            logger.error("orchestrate transport_error: %s", exc)
            return _unavailable()

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": (response.text or "")[:400]}

        if response.status_code >= 400:
            detail = payload.get("error") if isinstance(payload, dict) else None
            return CallResult(
                ok=False,
                payload=payload,
                status_code=response.status_code,
                error_detail=str(
                    detail or (response.text or "")[:200] or response.reason_phrase
                ),
            )

        if isinstance(payload, dict):
            status = payload.get("status")
            error = payload.get("error")
            if error and status not in (None, 200, "200"):
                return CallResult(
                    ok=False,
                    payload=payload,
                    status_code=int(status) if str(status).isdigit() else response.status_code,
                    error_detail=str(error),
                )
        return CallResult(
            ok=True,
            payload=payload,
            status_code=response.status_code,
            ticket_id=_ticket_id(payload),
        )

    def get_saldo_horas(self, chapa: str) -> CallResult:
        return self._call("GET", f"/gep/saldo-horas/{chapa}")

    def consulta_documentos(self, *, chapa: str, keyword: str) -> CallResult:
        return self._call(
            "POST",
            "/gpg/consulta-documentos",
            body={"chapa": chapa, "keyword": keyword, "qt": "search", "range": 0},
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> CallResult:
        return self._call("GET", path, params=params)

    def post_json(self, path: str, body: dict[str, Any]) -> CallResult:
        return self._call("POST", path, body=body)


def _ticket_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("ticketId", "NUM_CHAMADO", "protocolo", "WSCHAMADO"):
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    for key in ("data", "M4"):
        found = _ticket_id(payload.get(key))
        if found:
            return found
    dados = payload.get("DADOS")
    if isinstance(dados, dict):
        return _ticket_id(dados)
    return None


def _unavailable() -> CallResult:
    return CallResult(
        ok=False,
        status_code=503,
        error_detail="serviço de integração temporariamente indisponível",
    )


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

    def get_saldo_horas(self, chapa: str) -> CallResult:
        return CallResult(
            ok=True,
            payload={"Saldo Anterior": "10:00", "Saldo Atual": "08:00", "chapa": chapa},
        )

    def consulta_documentos(self, *, chapa: str, keyword: str) -> CallResult:
        return CallResult(
            ok=True,
            payload={
                "chapa": chapa,
                "resultDocumentos": {
                    "strDocumentos": f"Documento de exemplo para {keyword}.",
                },
            },
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> CallResult:
        if path == "/gef/lista-origem":
            options = [{"label": "Presencial", "value": "Presencial"}]
            return CallResult(ok=True, payload={"status": 200, "options": options})
        if path == "/gef/lista-modalidade":
            options = [{"label": "Curso técnico", "value": "Curso técnico"}]
            return CallResult(ok=True, payload={"status": 200, "options": options})
        if path == "/gef/lista-curso":
            options = [{"label": "Administração", "value": "Administração"}]
            return CallResult(ok=True, payload={"status": 200, "options": options})
        if path == "/gef/lista-ficha-tecnica":
            return CallResult(
                ok=True,
                payload={
                    "status": 200,
                    "list": [
                        [
                            "Centro de custo: 123. Título: Administração.",
                            "123",
                        ]
                    ],
                },
            )
        if path == "/gef/relatorios/conciliacao-caixa/lista":
            return CallResult(
                ok=True,
                payload={
                    "status": 200,
                    "data": {
                        "data": {
                            "DADOS": [
                                {
                                    "caixa": "01",
                                    "registradora": "1",
                                    "descrCaixa": "Caixa teste",
                                }
                            ]
                        }
                    },
                },
            )
        return CallResult(ok=True, payload={"status": 200, "params": params or {}, "path": path})

    def post_json(self, path: str, body: dict[str, Any]) -> CallResult:
        if "abertura-chamado" in path or path.endswith("/relatorios/solicitar"):
            return CallResult(
                ok=False,
                status_code=503,
                error_detail="mock não devolve protocolo",
            )
        return CallResult(ok=True, payload={"status": 200, "body": body, "path": path})


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
