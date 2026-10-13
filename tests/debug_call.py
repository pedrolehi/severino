"""Script de diagnóstico e depuração direta de chamadas HTTP para o senac-orchestrate.

Permite inspecionar requisições e respostas brutas (headers, body e erros upstream)
para entender exatamente o motivo de status 500 ou falhas de integração.

Uso:
    python -m tests.debug_call --all
    python -m tests.debug_call --classify 10001047
    python -m tests.debug_call --flow crachas
    python -m tests.debug_call --flow ponto
    python -m tests.debug_call --endpoint /gef/lista-origem
    python -m tests.debug_call --endpoint /gep/saldo-horas/11796
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Garante raiz do repositório no sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Carrega variáveis do .env se existir
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

import httpx

from flows.payload import pessoa_body
from flows.session import normalize_user_info
from tests.config import TEST_USER_INFO


def _print_divider(char: str = "=", length: int = 80) -> None:
    print(char * length)


def _format_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return str(data)


def execute_http_call(
    method: str,
    base_url: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    _print_divider("=")
    print(f"🚀 REQUISIÇÃO: {method} {url}")
    _print_divider("-")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"Headers enviados:\n{_format_json(headers)}")
    if params:
        print(f"Query Params:\n{_format_json(params)}")
    if body:
        print(f"Request Body:\n{_format_json(body)}")

    t0 = time.perf_counter()
    try:
        resp = httpx.request(
            method=method,
            url=url,
            params=params,
            json=body,
            headers=headers,
            timeout=timeout,
        )
        duration_ms = (time.perf_counter() - t0) * 1000
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        _print_divider("-")
        print(f"❌ ERRO DE TRANSPORTE / CONEXÃO ({duration_ms:.0f}ms): {exc}")
        _print_divider("=")
        return {"ok": False, "status": 0, "error": str(exc)}

    _print_divider("-")
    status_emoji = "✅" if resp.status_code == 200 else "🚨"
    print(f"RESPOSTA RECEBIDA ({duration_ms:.0f}ms): {status_emoji} HTTP {resp.status_code} {resp.reason_phrase}")
    print(f"Response Headers:\n{_format_json(dict(resp.headers))}")

    try:
        payload = resp.json()
        print(f"Response JSON Body:\n{_format_json(payload)}")
    except Exception:
        payload = {"raw_text": resp.text}
        print(f"Response Raw Text (não-JSON):\n{resp.text[:2000]}")

    _print_divider("-")

    # Diagnóstico específico de erro
    if resp.status_code >= 400 or (isinstance(payload, dict) and payload.get("status") not in (None, 200, "200")):
        print("🔍 ANÁLISE DE DIAGNÓSTICO DO ERRO:")
        if isinstance(payload, dict):
            status_val = payload.get("status") or payload.get("statusCode")
            error_val = payload.get("error")
            msg_val = payload.get("message")
            data_val = payload.get("data")
            url_val = payload.get("url")

            print(f" • Status retornado no payload: {status_val}")
            print(f" • Mensagem de Erro:             {error_val or msg_val}")
            if url_val:
                print(f" • URL externa chamada (upstream): {url_val}")
            if data_val:
                print(f" • Dados da API externa (data):\n   {_format_json(data_val)}")
        else:
            print(f" • Corpo cru da resposta: {resp.text[:500]}")
    else:
        print("✨ Requisição completada com sucesso!")

    _print_divider("=")
    print()

    return {
        "ok": resp.status_code == 200,
        "status": resp.status_code,
        "duration_ms": duration_ms,
        "payload": payload,
    }


def debug_classify(base_url: str, classification_id: str) -> None:
    print(f"\n🔎 Depurando Classificação ICD para ID: '{classification_id}'")
    execute_http_call(
        "POST",
        base_url,
        "/tools/classify-icd",
        body={"context": {"classificationId": classification_id}},
    )


def debug_ticket_gep(base_url: str, flow_type: str = "crachas") -> None:
    info = normalize_user_info(TEST_USER_INFO)

    configs = {
        "crachas": {
            "tipo": "Segunda via de crachá",
            "classification": "10001047",
            "texto": "[TESTE QA DEBUG] Meu crachá quebrou na catraca.",
            "tema": "Crachá",
            "subtema": "",
        },
        "ponto": {
            "tipo": "Problemas com batida de ponto",
            "classification": "10001048",
            "texto": "[TESTE QA DEBUG] Esqueci de bater ponto na entrada.",
            "tema": "Ponto Eletrônico",
            "subtema": "Esquecimento de marcação",
        },
        "beneficios": {
            "tipo": "Dúvidas sobre Vale Transporte",
            "classification": "10001049",
            "texto": "[TESTE QA DEBUG] Problema no carregamento do vale transporte.",
            "tema": "Benefícios",
            "subtema": "Vale Transporte",
        },
    }

    cfg = configs.get(flow_type, configs["crachas"])

    print(f"\n📋 1. Passo prévio: Classificar ICD para '{cfg['classification']}'...")
    classify_res = execute_http_call(
        "POST",
        base_url,
        "/tools/classify-icd",
        body={"context": {"classificationId": cfg["classification"]}},
    )

    body = pessoa_body(
        info,
        tipo=cfg["tipo"],
        classification=cfg["classification"],
        texto=cfg["texto"],
        tema=cfg["tema"],
        subtema=cfg["subtema"],
    )

    # Se classify-icd trouxe metadados, injeta
    if classify_res.get("ok"):
        pl = classify_res.get("payload") or {}
        data = pl.get("data")
        dados = data.get("DADOS") if isinstance(data, dict) else pl.get("DADOS")
        if isinstance(dados, dict):
            if dados.get("COMMODITY"):
                body["COMMODITY"] = dados["COMMODITY"]
            if dados.get("COMMODITYGROUP"):
                body["COMMODITYGROUP"] = dados["COMMODITYGROUP"]
            if dados.get("CLASSSTRUCTUREID"):
                body["CLASSSTRUCTUREID"] = dados["CLASSSTRUCTUREID"]

    print(f"\n📋 2. Submetendo abertura de chamado para fluxo '{flow_type}'...")
    execute_http_call(
        "POST",
        base_url,
        "/tools/abertura-chamado",
        body=body,
    )


def debug_all(base_url: str) -> None:
    print(f"\n🩺 Executando bateria rápida de diagnóstico contra {base_url}...\n")

    info = normalize_user_info(TEST_USER_INFO)
    chapa = TEST_USER_INFO.get("DADOS", {}).get("CHAPA", "11796")

    tests = [
        ("GET", "/gef/lista-origem", None, None),
        ("GET", f"/gep/saldo-horas/{chapa}", None, None),
        ("POST", "/tools/classify-icd", None, {"context": {"classificationId": "10001047"}}),
        ("POST", "/gpg/consulta-documentos", None, {"chapa": chapa, "keyword": "irpf", "qt": "search", "range": 0}),
    ]

    for method, path, params, body in tests:
        execute_http_call(method, base_url, path, params=params, body=body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnóstico e depuração detalhada de APIs do senac-orchestrate"
    )
    parser.add_argument(
        "--url",
        default="",
        help="URL base do senac-orchestrate (default: SENAC_ORCHESTRATE_URL do .env)",
    )
    parser.add_argument(
        "--classify",
        metavar="ID",
        help="Testa /tools/classify-icd com o ID informado (ex: 10001047)",
    )
    parser.add_argument(
        "--flow",
        choices=["crachas", "ponto", "beneficios"],
        help="Testa o fluxo completo de abertura de chamado (classify + abertura-chamado)",
    )
    parser.add_argument(
        "--endpoint",
        metavar="PATH",
        help="Chama um endpoint avulso (ex: /gef/lista-origem ou /gep/saldo-horas/11796)",
    )
    parser.add_argument(
        "--method",
        default="GET",
        choices=["GET", "POST"],
        help="Método HTTP para o endpoint avulso (default: GET)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Executa diagnóstico de todos os endpoints principais",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.url or os.getenv("SENAC_ORCHESTRATE_URL", "").strip()

    if not base_url:
        print("❌ Erro: Nenhuma URL de orchestrate configurada.")
        print("Defina SENAC_ORCHESTRATE_URL no .env ou passe via --url <url>")
        return 1

    print(f"🔧 Conectando em: {base_url}")

    if args.classify:
        debug_classify(base_url, args.classify)
    elif args.flow:
        debug_ticket_gep(base_url, args.flow)
    elif args.endpoint:
        execute_http_call(args.method, base_url, args.endpoint)
    elif args.all:
        debug_all(base_url)
    else:
        # Default: se nenhum argumento for passado, executa debug do fluxo crachás
        print("ℹ️ Nenhum argumento específico informado. Executando debug do fluxo 'crachas'...")
        debug_ticket_gep(base_url, "crachas")

    return 0


if __name__ == "__main__":
    sys.exit(main())
