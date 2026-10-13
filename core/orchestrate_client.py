import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0


def _format_payload_for_log(data: Any, max_length: int = 1200) -> str:
    if data is None:
        return "null"
    if isinstance(data, (dict, list)):
        try:
            dumped = json.dumps(data, ensure_ascii=False, indent=2)
            if len(dumped) > max_length:
                return dumped[:max_length] + f"... (truncado, total {len(dumped)} caracteres)"
            return dumped
        except Exception:
            pass
    text = str(data)
    if len(text) > max_length:
        return text[:max_length] + f"... (truncado, total {len(text)} caracteres)"
    return text


def _extract_error_detail(
    status_code: int,
    payload: Any,
    raw_text: str = "",
) -> tuple[int, str]:
    """Extrai código de status real e mensagem de erro estruturada com dados de upstream."""
    effective_status = status_code
    parts: list[str] = []

    if isinstance(payload, dict):
        # 1. Tenta identificar status code interno da API ou gateway
        for key in ("status", "statusCode", "CODIGO", "status_code"):
            val = payload.get(key)
            if val is not None and str(val).isdigit():
                parsed_val = int(val)
                if parsed_val >= 400:
                    effective_status = parsed_val
                    break

        # 2. Coleta mensagem primária de erro
        primary_msg = None
        for key in ("error", "message", "MENSAGEM", "mensagem", "detail", "details", "WSRETURNDETAIL"):
            val = payload.get(key)
            if val and isinstance(val, (str, int, float)):
                clean_val = str(val).strip()
                if clean_val and clean_val.lower() not in {"internal server error", "error"}:
                    primary_msg = clean_val
                    break
        if not primary_msg and payload.get("error"):
            primary_msg = str(payload["error"]).strip()
        elif not primary_msg and payload.get("message"):
            primary_msg = str(payload["message"]).strip()

        if primary_msg:
            parts.append(primary_msg)

        # 3. Coleta campos 'data' / 'DADOS' / 'details' onde residem respostas das APIs externas do Senac/Maximo
        for extra_key in ("data", "DADOS", "details", "raw"):
            extra = payload.get(extra_key)
            if not extra:
                continue
            if isinstance(extra, dict):
                sub_msg = (
                    extra.get("MENSAGEM")
                    or extra.get("mensagem")
                    or extra.get("error")
                    or extra.get("message")
                    or extra.get("WSRETURNDETAIL")
                )
                sub_code = extra.get("CODIGO") or extra.get("codigo") or extra.get("WSSTATUSCODE")
                if sub_msg or sub_code:
                    parts.append(f"[upstream {extra_key}: code={sub_code} msg='{sub_msg}']")
                try:
                    parts.append(f"{extra_key}={json.dumps(extra, ensure_ascii=False)}")
                except Exception:
                    parts.append(f"{extra_key}={str(extra)}")
            elif isinstance(extra, str) and extra.strip() and extra.strip() != primary_msg:
                parts.append(f"{extra_key}={extra.strip()}")
            elif isinstance(extra, list) and extra:
                try:
                    parts.append(f"{extra_key}={json.dumps(extra, ensure_ascii=False)}")
                except Exception:
                    parts.append(f"{extra_key}={str(extra)}")

        if payload.get("url"):
            parts.append(f"upstream_url={payload.get('url')}")
    elif raw_text:
        cleaned_raw = raw_text.strip()
        if cleaned_raw:
            parts.append(cleaned_raw[:600])

    if not parts:
        parts.append(f"Erro HTTP {effective_status}")

    full_detail = f"[HTTP {effective_status}] " + " | ".join(parts)
    return effective_status, full_detail


def _log_http_error_diagnostic(
    method: str,
    url: str,
    status_code: int,
    error_detail: str,
    body: Any = None,
    params: Any = None,
    payload: Any = None,
) -> None:
    logger.error(
        "orchestrate error: %s %s status=%s detail=%s",
        method,
        url,
        status_code,
        error_detail,
    )
    border = "=" * 78
    print(
        f"\n{border}\n"
        f"🚨 [ORCHESTRATE HTTP ERROR] {method} {url}\n"
        f"   HTTP Status:     {status_code}\n"
        f"   Detalhe do Erro: {error_detail}\n"
        f"   Payload Enviado: {_format_payload_for_log(body or params, max_length=600)}\n"
        f"   Resposta API:    {_format_payload_for_log(payload, max_length=1500)}\n"
        f"{border}\n",
        flush=True,
    )


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
            eff_status, error_detail = _extract_error_detail(
                response.status_code,
                None,
                response.text,
            )
            _log_http_error_diagnostic(
                "GET",
                url,
                eff_status,
                error_detail,
                params=params,
                payload=response.text,
            )
            return NotaFiscalResult(
                ok=False,
                status_code=eff_status,
                error_detail=error_detail,
            )

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        status_http, links, error = _extract_links(payload)
        if error:
            _log_http_error_diagnostic(
                "GET",
                url,
                status_http or 500,
                error,
                params=params,
                payload=payload,
            )
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
        timeout = httpx.Timeout(self._timeout, connect=5.0)
        try:
            response = httpx.request(
                method,
                url,
                params=params,
                json=body,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            logger.error("orchestrate transport_error: %s", exc)
            _log_http_error_diagnostic(
                method,
                url,
                503,
                f"Falha de transporte / conexão: {exc}",
                body=body,
                params=params,
            )
            return _unavailable()

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": (response.text or "")[:1000]}

        if response.status_code >= 400:
            eff_status, error_detail = _extract_error_detail(
                response.status_code,
                payload,
                response.text,
            )
            _log_http_error_diagnostic(
                method,
                url,
                eff_status,
                error_detail,
                body=body,
                params=params,
                payload=payload,
            )
            return CallResult(
                ok=False,
                payload=payload,
                status_code=eff_status,
                error_detail=error_detail,
            )

        if isinstance(payload, dict):
            status = payload.get("status")
            error = payload.get("error")
            codigo = payload.get("CODIGO")
            has_error = bool(error) or (
                status not in (None, 200, "200") and str(status).isdigit() and int(status) >= 400
            ) or (
                codigo not in (None, 200, "200") and str(codigo).isdigit() and int(codigo) >= 400
            )
            if has_error:
                eff_status, error_detail = _extract_error_detail(
                    response.status_code,
                    payload,
                    response.text,
                )
                _log_http_error_diagnostic(
                    method,
                    url,
                    eff_status,
                    error_detail,
                    body=body,
                    params=params,
                    payload=payload,
                )
                return CallResult(
                    ok=False,
                    payload=payload,
                    status_code=eff_status,
                    error_detail=error_detail,
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

    def classify_icd(self, classification_id: str) -> dict[str, str]:
        res = self._call(
            "POST",
            "/tools/classify-icd",
            body={"context": {"classificationId": classification_id}},
        )
        if not res.ok or not isinstance(res.payload, dict):
            print(
                f"⚠️ [CLASSIFY-ICD] Falha ao consultar metadados para '{classification_id}'. "
                f"Status: {res.status_code} | Detalhes: {res.error_detail}",
                flush=True,
            )
            return {}
        data = res.payload.get("data")
        dados = data.get("DADOS") if isinstance(data, dict) else res.payload.get("DADOS")
        if isinstance(dados, dict):
            meta = {
                "COMMODITY": str(dados.get("COMMODITY") or ""),
                "COMMODITYGROUP": str(dados.get("COMMODITYGROUP") or ""),
                "CLASSIFICATIONID": str(dados.get("CLASSIFICATIONID") or classification_id),
                "CLASSSTRUCTUREID": str(dados.get("CLASSSTRUCTUREID") or ""),
            }
            logger.info("classify_icd resolvido para %s: %s", classification_id, meta)
            return meta
        print(
            f"⚠️ [CLASSIFY-ICD] Resposta não continha 'DADOS' para '{classification_id}': {res.payload}",
            flush=True,
        )
        return {}

    def open_ticket(self, body: dict[str, Any]) -> CallResult:
        payload = dict(body)
        classification_id = payload.get("classificationId") or payload.get("CLASSIFICATIONID")
        if classification_id and not payload.get("CLASSSTRUCTUREID"):
            icd_meta = self.classify_icd(str(classification_id))
            if icd_meta:
                if icd_meta.get("COMMODITY") and not payload.get("COMMODITY"):
                    payload["COMMODITY"] = icd_meta["COMMODITY"]
                if icd_meta.get("COMMODITYGROUP") and not payload.get("COMMODITYGROUP"):
                    payload["COMMODITYGROUP"] = icd_meta["COMMODITYGROUP"]
                if icd_meta.get("CLASSSTRUCTUREID") and not payload.get("CLASSSTRUCTUREID"):
                    payload["CLASSSTRUCTUREID"] = icd_meta["CLASSSTRUCTUREID"]
                if icd_meta.get("CLASSIFICATIONID") and not payload.get("CLASSIFICATIONID"):
                    payload["CLASSIFICATIONID"] = icd_meta["CLASSIFICATIONID"]
            else:
                logger.warning(
                    "open_ticket: prosseguindo sem classStructureId pois classify_icd não retornou metadados."
                )

        nome = str(payload.get("REPORTEDBY") or payload.get("nome") or "").strip()
        email = str(payload.get("REPORTEDEMAIL") or payload.get("email") or "").strip()
        unidade = str(payload.get("LOCATION") or payload.get("unidade") or "CAS").strip()
        classification = str(payload.get("CLASSIFICATIONID") or payload.get("classificationId") or "").strip()
        class_structure_id = str(payload.get("CLASSSTRUCTUREID") or payload.get("classStructureId") or "").strip()
        commodity = str(payload.get("COMMODITY") or payload.get("commodity") or "").strip()
        commodity_group = str(payload.get("COMMODITYGROUP") or payload.get("commodityGroup") or "").strip()
        description = str(payload.get("DESCRIPTION") or payload.get("shortDescription") or payload.get("tipo_chamado") or "").strip()
        long_description = str(
            payload.get("DESCRIPTION_LONGDESCRIPTION")
            or payload.get("longDescription")
            or payload.get("texto")
            or ""
        ).strip()

        clean_payload: dict[str, Any] = {
            "CREATEDBY": "MXINTADM",
            "EXTERNALSYSTEM": "CATÁLOGO DE SERVIÇOS",
            "MEIO_DE_ABERTURA": "Assistente Virtual do Senac - Administrativo",
            "REPORTEDBY": nome,
            "AFFECTEDPERSON": nome,
            "REPORTEDEMAIL": email,
            "AFFECTEDEMAIL": email,
            "CLASSIFICATIONID": classification,
            "CLASSSTRUCTUREID": class_structure_id,
            "COMMODITY": commodity,
            "COMMODITYGROUP": commodity_group,
            "DESCRIPTION": description,
            "DESCRIPTION_LONGDESCRIPTION": long_description,
            "LOCATION": unidade,
            "CURSO": "",
            "UNIDADE_CURSO": "",
            "SNCCODIGOOFERTA": "",
            "SNCINSCRICAO": "",
        }

        # Specs apenas se preenchidas e com itens
        specs = payload.get("TICKETSPECS") or payload.get("ticketSpecs")
        if isinstance(specs, list) and len(specs) > 0:
            clean_payload["TICKETSPECS"] = specs

        # Anexo apenas se preenchido
        anexo = payload.get("anexo")
        if anexo and isinstance(anexo, (dict, str)) and bool(anexo):
            clean_payload["anexo"] = anexo

        return self.post_json("/tools/abertura-chamado", clean_payload)


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
            options = [{"label": "GD", "value": "GD"}, {"label": "Presencial", "value": "Presencial"}]
            return CallResult(ok=True, payload={"status": 200, "options": options})
        if path == "/gef/lista-modalidade":
            options = [
                {"label": "APERFEIÇOAMENTO", "value": "APERFEIÇOAMENTO"},
                {"label": "Curso técnico", "value": "Curso técnico"},
            ]
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
            ticket = f"MOCK-ICD-{int(time.time() * 1000) % 1000000:06d}"
            return CallResult(
                ok=True,
                status_code=200,
                ticket_id=ticket,
                payload={"status": 200, "ticket_id": ticket, "body": body},
            )
        return CallResult(ok=True, payload={"status": 200, "body": body, "path": path})

    def classify_icd(self, classification_id: str) -> dict[str, str]:
        return {
            "COMMODITY": "015004",
            "COMMODITYGROUP": "015",
            "CLASSIFICATIONID": classification_id,
            "CLASSSTRUCTUREID": "31261",
        }

    def open_ticket(self, body: dict[str, Any]) -> CallResult:
        ticket = f"MOCK-ICD-{int(time.time() * 1000) % 1000000:06d}"
        return CallResult(
            ok=True,
            status_code=200,
            ticket_id=ticket,
            payload={"status": 200, "ticket_id": ticket, "body": body},
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
