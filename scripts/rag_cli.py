import _bootstrap  # noqa: F401

import argparse

from assistants.registry import get_assistant_by_id, list_assistant_ids
from rag.pipeline import format_chunks_debug, run_rag_subgraph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLI de debug RAG — mostra resposta e chunks recuperados",
    )
    parser.add_argument(
        "--assistant",
        default="intranet",
        help="ID do assistant (ex: intranet, portal_aluno)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista assistants disponíveis",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Pergunta única (modo não interativo)",
    )
    parser.add_argument(
        "--truncate",
        type=int,
        default=None,
        metavar="N",
        help="Limita preview de cada chunk a N caracteres",
    )
    return parser.parse_args()


def run_query(
    *,
    assistant_id: str,
    query: str,
    truncate: int | None,
) -> None:
    final_state = run_rag_subgraph(assistant_id=assistant_id, query=query)

    if final_state.get("fallback_reason"):
        print(f"Fallback ({final_state.get('fallback_source')}): {final_state.get('fallback_reason')}")
        if final_state.get("fallback_hint"):
            print(f"Hint: {final_state.get('fallback_hint')}")
        print(f"Tentativas de busca: {(final_state.get('search_attempt') or 0) + 1}")
        history = final_state.get("search_history") or []
        for item in history:
            print(
                f"  - attempt={item.get('attempt')} sim={item.get('top_similarity')} "
                f"q={item.get('search_query')!r}"
            )
        return

    rag_result = final_state.get("rag_result") or {}
    print(f"Assistant: {rag_result.get('answer', '')}")
    chunks = [
        {
            "id": c.get("id"),
            "content": c.get("content"),
            "score": c.get("score"),
            "similarity": c.get("similarity"),
            "metadata": c.get("metadata"),
        }
        for c in (final_state.get("chunks") or [])
    ]
    from rag.ports import RetrievedChunk

    parsed_chunks = [
        RetrievedChunk(
            id=str(c["id"]),
            content=str(c["content"]),
            score=float(c["score"]),
            metadata=dict(c["metadata"] or {}),
            similarity=float(c["similarity"]),
        )
        for c in chunks
    ]
    print(
        format_chunks_debug(
            parsed_chunks,
            collection_name=str(
                rag_result.get("collection_name")
                or final_state.get("collection_name")
                or ""
            ),
            truncate=truncate,
        )
    )
    print(f"Tentativas: {rag_result.get('search_attempts', 1)} | judge: {rag_result.get('judge_action')}")


def main() -> None:
    args = parse_args()

    if args.list:
        for assistant_id in list_assistant_ids():
            print(assistant_id)
        return

    get_assistant_by_id(args.assistant)

    if args.query:
        run_query(
            assistant_id=args.assistant,
            query=args.query,
            truncate=args.truncate,
        )
        return

    print(f"RAG debug | assistant={args.assistant}")
    print("Digite a pergunta. (sair / exit / quit para encerrar)")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_input:
            continue
        if user_input.lower() in {"sair", "exit", "quit"}:
            break

        run_query(
            assistant_id=args.assistant,
            query=user_input,
            truncate=args.truncate,
        )


if __name__ == "__main__":
    main()
