import argparse
import uuid

from langchain_core.messages import HumanMessage

from assistants.registry import get_assistant_by_id, list_assistant_ids
from core.hub import build_thread_id, get_graph


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list:
        for assistant_id in list_assistant_ids():
            print(assistant_id)
        return

    get_assistant_by_id(args.assistant)
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
