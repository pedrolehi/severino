import _bootstrap  # noqa: F401

import argparse
import uuid

from langchain_core.messages import HumanMessage

from assistants.registry import get_assistant_by_id, list_assistant_ids
from core.hub import build_thread_id, get_graph
from rag.pipeline import format_chunks_debug, run_rag_for_assistant_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chat CLI multi-assistant")
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
        "--rag-debug",
        action="store_true",
        help="Modo debug RAG: resposta + chunks recuperados (sem router)",
    )
    parser.add_argument(
        "--truncate",
        type=int,
        default=None,
        metavar="N",
        help="Com --rag-debug: limita preview de cada chunk a N caracteres",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list:
        for assistant_id in list_assistant_ids():
            print(assistant_id)
        return

    get_assistant_by_id(args.assistant)

    if args.rag_debug:
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

            rag_result = run_rag_for_assistant_id(
                assistant_id=args.assistant,
                query=user_input,
            )
            print(f"Assistant: {rag_result.answer}")
            print(
                format_chunks_debug(
                    list(rag_result.chunks),
                    collection_name=rag_result.collection_name,
                    truncate=args.truncate,
                )
            )
        return

    graph = get_graph(args.assistant)

    session_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": build_thread_id(args.assistant, session_id),
        }
    }

    print(f"Assistant: {args.assistant}")
    print(f"Session {session_id} started. (Ctrl+C to exit)")

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

        result = graph.invoke(
            {
                "assistant_id": args.assistant,
                "session_id": session_id,
                "messages": [HumanMessage(content=user_input)],
            },
            config=config,
        )

        reply = result["messages"][-1].content
        print(f"Assistant: {reply}")


if __name__ == "__main__":
    main()
