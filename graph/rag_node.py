import sys

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from core.config import APP_ENV
from graph.state import MultiAgentState
from rag.conversation import build_conversation_from_messages
from rag.pipeline import run_rag_subgraph


def rag_subgraph_node(
    state: MultiAgentState, config: RunnableConfig | None = None
) -> dict:
    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id não encontrado no estado")

    last_message = state["messages"][-1]
    if not isinstance(last_message, HumanMessage):
        raise TypeError("Última mensagem deve ser do usuário para RAG")

    content = last_message.content
    query = content if isinstance(content, str) else str(content)
    app_env = (state.get("app_env") or APP_ENV or "dev").strip().lower()
    conversation = build_conversation_from_messages(state.get("messages") or [])
    configurable = (config or {}).get("configurable") or {}
    token_queue = configurable.get("token_queue")
    use_stream = bool(state.get("rag_stream", True))
    print(
        f"[RAG] assistant={assistant_id}, app_env={app_env}, "
        f"query={query[:80]!r}, conversation_turns={len(conversation)} "
        f"(pipeline /rag/answer{'/stream' if use_stream else ''})"
        f" sse_queue={'on' if token_queue is not None else 'off'}",
        file=sys.stderr if use_stream else sys.stdout,
        flush=True,
    )

    writer = None
    if use_stream:
        try:
            writer = get_stream_writer()
        except Exception:  # noqa: BLE001 — fora de stream context
            writer = None

    # Tokens direto no stdout: LangGraph bufferiza custom events ate o no acabar,
    # o que invertia ordem (logs no meio / depois da resposta).
    printed_prefix = False
    streamed_parts: list[str] = []

    def on_token(text: str) -> None:
        nonlocal printed_prefix
        if not text:
            return
        streamed_parts.append(text)
        if token_queue is not None:
            token_queue.put({"event": "token", "text": text})
            return
        if not printed_prefix:
            print(flush=True)
            print("Assistant: ", end="", flush=True)
            printed_prefix = True
        print(text, end="", flush=True)
        if writer is not None:
            writer({"type": "token", "text": text})

    def on_step(event: dict) -> None:
        step_id = event.get("id") or "?"
        status = event.get("status") or ""
        dur = event.get("duration_ms")
        dur_s = f" {dur}ms" if isinstance(dur, (int, float)) else ""
        print(
            f"[STREAM] step={step_id} status={status}{dur_s}",
            file=sys.stderr,
            flush=True,
        )
        if token_queue is not None:
            token_queue.put(dict(event))
        if writer is not None:
            writer({"type": "step", **event})

    result = run_rag_subgraph(
        assistant_id=assistant_id,
        query=query,
        app_env=app_env,
        session_id=state.get("session_id"),
        conversation=conversation,
        stream=use_stream,
        on_token=on_token if use_stream else None,
        on_step=on_step if use_stream else None,
    )
    if printed_prefix:
        print(flush=True)
        final_text = ""
        for message in reversed(result.get("messages") or []):
            content = getattr(message, "content", None)
            if content:
                final_text = str(content).strip()
                break
        if not final_text:
            final_text = str(
                (result.get("rag_result") or {}).get("draft_answer") or ""
            ).strip()
        streamed_text = "".join(streamed_parts).strip()
        # Judge/repair pode mudar o draft streamado — mostra versao final.
        if final_text and final_text != streamed_text:
            print(
                f"\n[judge] resposta ajustada:\n{final_text}\n",
                flush=True,
            )

    update: dict = {
        "query": query,
        "app_env": app_env,
        "search_query": result.get("search_query"),
        "search_attempt": result.get("search_attempt"),
        "search_history": result.get("search_history"),
        "collection_name": result.get("collection_name"),
        "chunks": result.get("chunks"),
        "citations": result.get("citations"),
        "retrieval_metrics": result.get("retrieval_metrics"),
        "rag_result": result.get("rag_result"),
        "fallback_reason": result.get("fallback_reason"),
        "fallback_source": result.get("fallback_source"),
        "fallback_hint": result.get("fallback_hint"),
        # CLI: evita reimprimir tokens que ja foram pro stdout
        "rag_streamed": printed_prefix,
    }
    if result.get("messages"):
        update["messages"] = result["messages"]
    return update
