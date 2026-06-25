import _bootstrap  # noqa: F401

import argparse

from assistants.registry import get_assistant_by_id, list_assistant_ids
from rag.pipeline import format_chunks_debug, run_rag_for_assistant_id


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
    result = run_rag_for_assistant_id(assistant_id=assistant_id, query=query)
    print(f"Assistant: {result.answer}")
    print(
        format_chunks_debug(
            list(result.chunks),
            collection_name=result.collection_name,
            truncate=truncate,
        )
    )


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
