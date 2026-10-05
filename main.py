import json
import queue
import threading
import time
import uuid
from collections.abc import Iterator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from assistants.registry import get_assistant_by_id, list_assistant_ids
from core.config import APP_ENV
from core.hub import build_thread_id, get_graph
from flows.session import normalize_user_info

load_dotenv()


def _warm_startup() -> None:
    for assistant_id in list_assistant_ids():
        get_graph(assistant_id)


_warm_startup()

app = FastAPI(title="from-scratch-multiagent API")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    assistant_id: str = "intranet"
    user_id: str | None = None
    session_id: str | None = None
    user_info: dict | None = None


class ChatResponse(BaseModel):
    assistant_id: str
    session_id: str
    response: str
    route: str | None = None
    ui: list[dict] | None = None


def _route_from_result(result: dict) -> str | None:
    decision = result.get("decision") or {}
    route = decision.get("route")
    if isinstance(route, dict):
        route = route.get("choice")
    return route if isinstance(route, str) else None


def _last_ai_message(result: dict) -> AIMessage:
    messages = result.get("messages") or []
    last_ai = next(
        (message for message in reversed(messages) if isinstance(message, AIMessage)),
        None,
    )
    if last_ai is None:
        raise HTTPException(
            status_code=500, detail="Grafo não retornou mensagem do assistente"
        )
    return last_ai


def _response_text(result: dict) -> str:
    content = _last_ai_message(result).content
    return content if isinstance(content, str) else str(content)


def _response_ui(result: dict) -> list[dict] | None:
    raw = (_last_ai_message(result).additional_kwargs or {}).get("ui")
    if not isinstance(raw, list):
        return None
    ui = [item for item in raw if isinstance(item, dict)]
    return ui or None


def _prepare(request: ChatRequest) -> tuple[str, dict, dict]:
    try:
        get_assistant_by_id(request.assistant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_id = request.session_id or str(uuid.uuid4())
    graph = get_graph(request.assistant_id)
    payload = {
        "assistant_id": request.assistant_id,
        "user_id": request.user_id,
        "session_id": session_id,
        "app_env": APP_ENV or "dev",
        "messages": [HumanMessage(content=request.message)],
    }
    user_info = normalize_user_info(request.user_info)
    if user_info:
        payload["user_info"] = user_info
    return session_id, graph, payload


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok", "service": "from-scratch-multiagent"}


@app.get("/assistants")
def list_assistants() -> dict[str, list[str]]:
    return {"assistants": list_assistant_ids()}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    session_id, graph, payload = _prepare(request)
    payload["rag_stream"] = False
    result = graph.invoke(
        payload,
        config={
            "configurable": {
                "thread_id": build_thread_id(request.assistant_id, session_id),
            }
        },
    )
    return ChatResponse(
        assistant_id=request.assistant_id,
        session_id=session_id,
        response=_response_text(result),
        route=_route_from_result(result),
        ui=_response_ui(result),
    )


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """SSE: step enquanto nao ha token; token durante o generate; done no fim."""
    session_id, graph, payload = _prepare(request)
    payload["rag_stream"] = True
    token_queue: queue.Queue[dict | str | None] = queue.Queue()
    holder: dict = {}

    def _run() -> None:
        try:
            holder["result"] = graph.invoke(
                payload,
                config={
                    "configurable": {
                        "thread_id": build_thread_id(
                            request.assistant_id, session_id
                        ),
                        "token_queue": token_queue,
                    },
                    "metadata": {"invoke_t0": time.perf_counter()},
                },
            )
        except Exception as exc:  # noqa: BLE001
            holder["error"] = str(exc)
        finally:
            token_queue.put(None)

    threading.Thread(target=_run, daemon=True).start()

    def _events() -> Iterator[str]:
        while True:
            piece = token_queue.get()
            if piece is None:
                break
            if isinstance(piece, str):
                piece = {"event": "token", "text": piece}
            yield "data: " + json.dumps(piece, ensure_ascii=False) + "\n\n"
        if holder.get("error"):
            yield (
                "data: "
                + json.dumps(
                    {"event": "error", "detail": holder["error"]},
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            return
        result = holder.get("result") or {}
        try:
            response_text = _response_text(result)
            response_ui = _response_ui(result)
        except HTTPException as exc:
            yield (
                "data: "
                + json.dumps(
                    {"event": "error", "detail": exc.detail},
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            return
        rag_result = result.get("rag_result") or {}
        citations = rag_result.get("citations") if isinstance(rag_result, dict) else []
        done = {
            "event": "done",
            "assistant_id": request.assistant_id,
            "session_id": session_id,
            "response": response_text,
            "route": _route_from_result(result),
            "citations": citations if isinstance(citations, list) else [],
            "ui": response_ui,
        }
        yield "data: " + json.dumps(done, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
