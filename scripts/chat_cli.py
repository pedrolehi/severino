import argparse
import time
import uuid
from typing import Any

from langchain_core.messages import HumanMessage

from assistants.registry import get_assistant_by_id, list_assistant_ids
from core.config import APP_ENV, SEARCH_VECTORY_URL
from core.hub import build_thread_id, get_graph
from rag.config import VECTORY_ENV_BY_APP_ENV
from rag.pipeline import format_chunks_debug, run_rag_subgraph
from rag.policy import resolve_rag_policy
from rag.ports import RetrievedChunk
from rag.project_store import resolve_assistant_collection


def _fmt_ms(ms: float) -> str:
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms:.0f}ms"


def _print_vectory_timings(rag_result: dict[str, Any] | None) -> None:
    if not rag_result:
        return
    timings = rag_result.get("timings_ms")
    if isinstance(timings, dict) and timings:
        parts = [
            f"{key}={_fmt_ms(float(val))}"
            for key, val in timings.items()
            if isinstance(val, (int, float))
        ]
        if parts:
            print(f"[TIMING]   vectory: {', '.join(parts)}")
    trace = rag_result.get("trace")
    if isinstance(trace, list):
        for step in trace:
            if not isinstance(step, dict):
                continue
            step_id = step.get("id") or step.get("label") or "?"
            duration = step.get("duration_ms")
            if isinstance(duration, (int, float)):
                print(f"[TIMING]   trace.{step_id}={_fmt_ms(float(duration))}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chat CLI multi-assistant")
    parser.add_argument(
        "--assistant",
        default="intranet",
        help="ID do assistant (ex: intranet, portal_aluno)",
    )
    parser.add_argument(
        "--env",
        choices=sorted(VECTORY_ENV_BY_APP_ENV.keys()),
        default=(APP_ENV if APP_ENV in VECTORY_ENV_BY_APP_ENV else "dev"),
        help=(
            "Ambiente do projeto Mongo para resolver a collection Milvus "
            "(dev→collections.dev, hml→homolog, prod→prod). Default: APP_ENV ou dev."
        ),
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


def _print_rag_target(assistant_id: str, app_env: str) -> None:
    assistant = get_assistant_by_id(assistant_id)
    policy = resolve_rag_policy(assistant)
    vectory_env = VECTORY_ENV_BY_APP_ENV[app_env]
    try:
        collection = resolve_assistant_collection(
            project_id=policy.project_id,
            app_env=app_env,
            collection_name=policy.collection_name,
        )
    except Exception as exc:  # noqa: BLE001
        collection = f"(erro: {exc})"
    print(
        f"RAG target | project={policy.project_id} app_env={app_env} "
        f"vectory_env={vectory_env} collection={collection} "
        f"url={SEARCH_VECTORY_URL}"
    )


def main() -> None:
    args = parse_args()

    if args.list:
        for assistant_id in list_assistant_ids():
            print(assistant_id)
        return

    get_assistant_by_id(args.assistant)
    app_env = args.env
    _print_rag_target(args.assistant, app_env)

    if args.rag_debug:
        print(f"RAG debug | assistant={args.assistant} env={app_env}")
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

            t0 = time.perf_counter()
            final_state = run_rag_subgraph(
                assistant_id=args.assistant,
                query=user_input,
                app_env=app_env,
            )
            total_ms = (time.perf_counter() - t0) * 1000
            if final_state.get("fallback_reason"):
                print(
                    f"Fallback ({final_state.get('fallback_source')}): "
                    f"{final_state.get('fallback_reason')}"
                )
                print(f"[TIMING] total={_fmt_ms(total_ms)}")
                continue

            rag_result = final_state.get("rag_result") or {}
            answer = (
                final_state.get("draft_answer") or rag_result.get("draft_answer") or ""
            )
            if not answer:
                messages = final_state.get("messages") or []
                for message in reversed(messages):
                    content = getattr(message, "content", None)
                    if content:
                        answer = str(content)
                        break
            print(f"[TIMING] rag_pipeline={_fmt_ms(total_ms)}")
            _print_vectory_timings(rag_result if isinstance(rag_result, dict) else None)
            print(f"Assistant: {answer}")
            print(
                f"[pipeline] status={rag_result.get('status')} "
                f"log_id={rag_result.get('log_id')!r} "
                f"chunks={rag_result.get('retrieved_chunk_count')}"
            )
            parsed_chunks = [
                RetrievedChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    distance=float(item.get("distance", item.get("score", 0))),
                    metadata=dict(item.get("metadata") or {}),
                    similarity=float(item.get("similarity", 0)),
                    adjusted_score=(
                        float(item["adjusted_score"])
                        if item.get("adjusted_score") is not None
                        else None
                    ),
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

        t0 = time.perf_counter()
        step_t = t0
        for update in graph.stream(
            {
                "assistant_id": args.assistant,
                "session_id": session_id,
                "app_env": app_env,
                "messages": [HumanMessage(content=user_input)],
            },
            config=config,
            stream_mode="updates",
        ):
            now = time.perf_counter()
            dt_ms = (now - step_t) * 1000
            cum_ms = (now - t0) * 1000
            if not isinstance(update, dict):
                step_t = now
                continue
            for node_name, payload in update.items():
                print(
                    f"[TIMING] step={node_name} "
                    f"dt={_fmt_ms(dt_ms)} cum={_fmt_ms(cum_ms)}"
                )
                if node_name == "rag_subgraph" and isinstance(payload, dict):
                    rag_result = payload.get("rag_result")
                    _print_vectory_timings(
                        rag_result if isinstance(rag_result, dict) else None
                    )
            step_t = now

        state = graph.get_state(config).values
        reply = state["messages"][-1].content
        total_ms = (time.perf_counter() - t0) * 1000
        print(f"[TIMING] total={_fmt_ms(total_ms)}")
        print(f"Assistant: {reply}")


if __name__ == "__main__":
    main()
