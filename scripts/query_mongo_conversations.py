"""Script para buscar conversas reais e dados de usuários no MongoDB.

Conecta ao cluster MongoDB do Senac (bancos 'orchestrate' e 'vectory')
para extrair chapas reais, dados cadastrais de colaboradores e exemplos de diálogos
bem-sucedidos para cada tema (GEP, GEF, GCR, GEDUC, GPG).

Uso:
    python -m scripts.query_mongo_conversations --pedro
    python -m scripts.query_mongo_conversations --theme cracha
    python -m scripts.query_mongo_conversations --theme ponto
    python -m scripts.query_mongo_conversations --successful
    python -m scripts.query_mongo_conversations --export tests/fixtures/real_conversations.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Garante raiz do repositório no sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

try:
    from pymongo import MongoClient
except ImportError:
    print("❌ Erro: 'pymongo' não está instalado. Instale com: pip install pymongo")
    sys.exit(1)


def _clean_text(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _extract_user_from_dict(doc: dict[str, Any]) -> dict[str, Any] | None:
    """Tenta extrair dados estruturados de colaborador de qualquer documento/contexto."""
    candidates = []

    # 1. Procura em context.user_info
    ctx = doc.get("context") or {}
    if isinstance(ctx, dict):
        ui = ctx.get("user_info") or {}
        if isinstance(ui, dict):
            dados = ui.get("DADOS") or ui
            if isinstance(dados, dict):
                candidates.append(dados)

    # 2. Procura em bot.context.user_info
    bot = doc.get("bot") or {}
    if isinstance(bot, dict):
        bot_ctx = bot.get("context") or {}
        if isinstance(bot_ctx, dict):
            ui = bot_ctx.get("user_info") or {}
            if isinstance(ui, dict):
                dados = ui.get("DADOS") or ui
                if isinstance(dados, dict):
                    candidates.append(dados)

    # 3. Procura no próprio doc
    candidates.append(doc)

    for item in candidates:
        chapa = item.get("CHAPA") or item.get("chapa")
        nome = item.get("NOME") or item.get("nome") or item.get("nomeCompleto")
        email = item.get("EMAIL") or item.get("email")
        cpf = item.get("CPF") or item.get("cpf")
        unidade = item.get("UNIDADE") or item.get("unidade") or item.get("sigla")

        if chapa or (nome and email):
            return {
                "chapa": _clean_text(chapa),
                "nome": _clean_text(nome),
                "email": _clean_text(email),
                "cpf": _clean_text(cpf),
                "unidade": _clean_text(unidade),
            }

    return None


def _find_ticket_protocol(text: str) -> str | None:
    """Detecta se uma mensagem do bot continha um protocolo real de chamado."""
    if not text:
        return None
    match = re.search(r"(?:protocolo|chamado|ticket)[\s:]+([A-Za-z0-9_\-\.]+)", text, re.IGNORECASE)
    if match:
        val = match.group(1).strip().rstrip(".")
        if len(val) >= 4 and val.lower() not in {"mock", "erro", "nenhum", "null", "false"}:
            return val
    return None


def get_mongo_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        print("❌ Erro: MONGODB_URI não encontrada no arquivo .env.")
        sys.exit(1)

    print("🔌 Conectando ao MongoDB...")
    client = MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000,
    )
    return client


def search_pedro_or_user(client: MongoClient, query: str = "pedro") -> list[dict[str, Any]]:
    print(f"\n🔍 Buscando usuário correspondente a '{query}' em todas as coleções...")
    results = []

    # Bancos a verificar
    db_names = ["orchestrate", "vectory"]
    try:
        available_dbs = client.list_database_names()
        for d in available_dbs:
            if d not in db_names and d not in {"admin", "local", "config"}:
                db_names.append(d)
    except Exception:
        pass

    regex = re.compile(re.escape(query), re.IGNORECASE)

    for db_name in db_names:
        db = client[db_name]
        try:
            col_names = db.list_collection_names()
        except Exception:
            continue

        for col_name in col_names:
            col = db[col_name]
            try:
                # Busca por email, nome ou texto
                filter_q = {
                    "$or": [
                        {"context.user_info.DADOS.EMAIL": regex},
                        {"context.user_info.DADOS.NOME": regex},
                        {"bot.context.user_info.DADOS.EMAIL": regex},
                        {"bot.context.user_info.DADOS.NOME": regex},
                        {"userInput": regex},
                        {"messages.content.text": regex},
                    ]
                }
                cursor = col.find(filter_q).limit(10)
                for doc in cursor:
                    user_data = _extract_user_from_dict(doc)
                    results.append(
                        {
                            "database": db_name,
                            "collection": col_name,
                            "user": user_data,
                            "doc_id": str(doc.get("_id")),
                            "sessionId": doc.get("sessionId"),
                            "snippet": str(doc.get("userInput") or "")[:200],
                        }
                    )
            except Exception:
                continue

    return results


def search_successful_conversations(
    client: MongoClient,
    theme_keyword: str | None = None,
    limit_per_theme: int = 5,
) -> list[dict[str, Any]]:
    print("\n🔍 Buscando conversas bem-sucedidas no banco 'orchestrate'...")

    themes = {
        "crachas": ["crachá", "cracha", "segunda via de crachá"],
        "ponto": ["ponto", "batida de ponto", "esqueci de bater"],
        "beneficios": ["benefício", "beneficio", "transporte", "refeição"],
        "carta_convite": ["carta convite", "convite"],
        "nota_fiscal": ["nota fiscal", "segunda via da nota"],
        "centro_de_custo": ["centro de custo"],
        "relatorios_orcamentarios": ["relatório orçamentário", "relatorio"],
        "gestao_pagamentos": ["pagamento", "gestão de pagamentos"],
        "saldo_horas": ["saldo de horas", "saldo", "banco de horas"],
        "geduc": ["geduc", "portaria"],
        "gcr": ["gcr"],
        "documentos": ["documento", "irpf", "informe"],
    }

    if theme_keyword:
        filtered_themes = {
            k: v for k, v in themes.items() if theme_keyword.lower() in k.lower() or any(theme_keyword.lower() in kw for kw in v)
        }
        if filtered_themes:
            themes = filtered_themes

    db = client["orchestrate"]
    candidate_collections = ["sessionconversations", "sessions"]
    try:
        for c in db.list_collection_names():
            if c.startswith("messages_") and c not in candidate_collections:
                candidate_collections.append(c)
    except Exception:
        pass

    results = []

    for theme_name, keywords in themes.items():
        print(f" • Varrendo tema '{theme_name}'...")
        theme_regex = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
        found_for_theme = 0

        for col_name in candidate_collections:
            if found_for_theme >= limit_per_theme:
                break
            col = db[col_name]
            try:
                # Procura documentos com o tema
                cursor = col.find(
                    {
                        "$or": [
                            {"userInput": theme_regex},
                            {"messages.content.text": theme_regex},
                            {"context.active_flow": re.compile(theme_name, re.IGNORECASE)},
                        ]
                    }
                ).limit(30)

                for doc in cursor:
                    user_info = _extract_user_from_dict(doc)

                    # Extrai turnos de mensagens
                    turns = []
                    messages = doc.get("messages") or []
                    if isinstance(messages, list) and messages:
                        for m in messages:
                            sender = m.get("sender") or "unknown"
                            content = m.get("content") or {}
                            text = content.get("text") if isinstance(content, dict) else str(content)
                            turns.append({"sender": sender, "text": text})
                    elif doc.get("userInput"):
                        turns.append({"sender": "user", "text": doc.get("userInput")})
                        bot_out = doc.get("bot", {}).get("output") or doc.get("botOutput")
                        if bot_out:
                            turns.append({"sender": "assistant", "text": str(bot_out)})

                    # Verifica se teve sucesso ou gerou protocolo
                    full_text = " ".join(t.get("text") or "" for t in turns)
                    protocol = _find_ticket_protocol(full_text)

                    if turns:
                        results.append(
                            {
                                "theme": theme_name,
                                "collection": col_name,
                                "sessionId": doc.get("sessionId"),
                                "user": user_info,
                                "protocol": protocol,
                                "turns": turns,
                            }
                        )
                        found_for_theme += 1
                        if found_for_theme >= limit_per_theme:
                            break
            except Exception:
                continue

    return results


def print_summary(client: MongoClient) -> None:
    print("\n📊 ESTATÍSTICAS DOS BANCOS E COLEÇÕES NO MONGODB:")
    print("=" * 65)
    try:
        dbs = client.list_database_names()
        for db_name in dbs:
            db = client[db_name]
            cols = db.list_collection_names()
            print(f"📦 Database: '{db_name}' ({len(cols)} coleções)")
            for col_name in cols:
                try:
                    count = db[col_name].estimated_document_count()
                    print(f"    • {col_name:<30} {count:>8} documentos")
                except Exception:
                    print(f"    • {col_name}")
            print()
    except Exception as exc:
        print(f"Erro ao listar estatísticas: {exc}")
    print("=" * 65)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explora MongoDB para extrair usuários reais e conversas bem-sucedidas"
    )
    parser.add_argument(
        "--pedro",
        action="store_true",
        help="Busca cadastro e conversas do usuário Pedro Muniz",
    )
    parser.add_argument(
        "--user",
        metavar="QUERY",
        help="Busca usuário específico por nome, email ou chapa",
    )
    parser.add_argument(
        "--theme",
        metavar="TEMA",
        help="Filtra por um tema específico (ex: crachas, ponto, nota_fiscal, saldo_horas)",
    )
    parser.add_argument(
        "--successful",
        action="store_true",
        help="Busca conversas bem-sucedidas por tema",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Exibe estatísticas dos bancos e contagem de documentos",
    )
    parser.add_argument(
        "--export",
        metavar="ARQUIVO_JSON",
        help="Salva as conversas encontradas em arquivo JSON para uso nos testes",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = get_mongo_client()

    if args.summary:
        print_summary(client)
        return 0

    if args.pedro or args.user:
        query = "pedro" if args.pedro else args.user
        results = search_pedro_or_user(client, query)
        print(f"\n🎯 Encontrados {len(results)} registros para '{query}':")
        print("=" * 70)
        found_users = set()
        for r in results:
            u = r.get("user")
            if u and u.get("email"):
                key = (u.get("chapa"), u.get("nome"), u.get("email"), u.get("cpf"), u.get("unidade"))
                if key not in found_users:
                    found_users.add(key)
                    print(f"👤 Colaborador Identificado:")
                    print(f"   • Chapa:   {u.get('chapa')}")
                    print(f"   • Nome:    {u.get('nome')}")
                    print(f"   • Email:   {u.get('email')}")
                    print(f"   • CPF:     {u.get('cpf')}")
                    print(f"   • Unidade: {u.get('unidade')}")
                    print(f"   • Origem:  DB {r.get('database')} / Col {r.get('collection')}")
                    print("-" * 70)

        if not found_users:
            print("Nenhum dado cadastral completo encontrado. Snippets:")
            for r in results[:5]:
                print(f"[{r.get('collection')}] {r.get('snippet')}")
        return 0

    # Busca conversas por tema
    theme_to_search = args.theme
    conversations = search_successful_conversations(client, theme_keyword=theme_to_search)

    print(f"\n🎉 Total de conversas catalogadas: {len(conversations)}")
    print("=" * 70)

    for c in conversations:
        u = c.get("user") or {}
        user_desc = f"{u.get('nome') or 'Anônimo'} (Chapa: {u.get('chapa') or 'N/A'}, Unidade: {u.get('unidade') or 'N/A'})"
        prot_desc = f" | Protocolo: {c.get('protocol')}" if c.get("protocol") else ""
        print(f"\n📂 [{c.get('theme').upper()}] em '{c.get('collection')}' {prot_desc}")
        print(f"   Usuário: {user_desc}")
        for t in c.get("turns", [])[:4]:
            speaker = "👤 Usuário" if t.get("sender") in {"user", "human"} else "🤖 Assistente"
            preview = t.get("text", "").replace("\n", " ")[:120]
            print(f"   {speaker}: {preview}")

    if args.export:
        export_path = BASE_DIR / args.export
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(conversations, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Conversas exportadas com sucesso para: {export_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
