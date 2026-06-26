import _bootstrap  # noqa: F401

import argparse
import uuid

from langchain_core.messages import HumanMessage

from assistants.registry import get_assistant_by_id, list_assistant_ids
from core.hub import build_thread_id, get_graph
from rag.pipeline import format_chunks_debug, run_rag_subgraph
from rag.ports import RetrievedChunk


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

            final_state = run_rag_subgraph(
                assistant_id=args.assistant,
                query=user_input,
            )
            if final_state.get("fallback_reason"):
                print(
                    f"Fallback ({final_state.get('fallback_source')}): "
                    f"{final_state.get('fallback_reason')}"
                )
                continue

            rag_result = final_state.get("rag_result") or {}
            print(f"Assistant: {final_state.get('draft_answer') or ''}")
            parsed_chunks = [
                RetrievedChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    score=float(item.get("score", 0)),
                    metadata=dict(item.get("metadata") or {}),
                    similarity=float(item.get("similarity", 0)),
                )
                for item in (final_state.get("chunks") or [])
            ]
            print(
                format_chunks_debug(
                    parsed_chunks,
                    collection_name=str(
                        rag_result.get("collection_name")
                        or final_state.get("collection_name")
                        or ""
                    ),
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
