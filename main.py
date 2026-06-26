import uuid
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from assistants.registry import get_assistant_by_id, list_assistant_ids
from core.hub import build_thread_id, get_graph

load_dotenv()

app = FastAPI(title="from-scratch-multiagent API")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    assistant_id: str = "intranet"
    user_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    assistant_id: str
    session_id: str
    response: str
    route: str | None = None
    fallback_reason: str | None = None
    fallback_source: str | None = None
    rag_result: dict[str, Any] | None = None


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok", "service": "from-scratch-multiagent"}


@app.get("/assistants")
def list_assistants() -> dict[str, list[str]]:
    return {"assistants": list_assistant_ids()}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    try:
        get_assistant_by_id(request.assistant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_id = request.session_id or str(uuid.uuid4())
    graph = get_graph(request.assistant_id)
    config = {
        "configurable": {
            "thread_id": build_thread_id(request.assistant_id, session_id),
        }
    }

    result = graph.invoke(
        {
            "assistant_id": request.assistant_id,
            "user_id": request.user_id,
            "session_id": session_id,
            "messages": [HumanMessage(content=request.message)],
        },
        config=config,
    )

    messages = result.get("messages") or []
    last_ai = next(
        (message for message in reversed(messages) if isinstance(message, AIMessage)),
        None,
    )
    if last_ai is None:
        raise HTTPException(status_code=500, detail="Grafo não retornou mensagem do assistente")

    content = last_ai.content
    response_text = content if isinstance(content, str) else str(content)

    decision = result.get("decision") or {}
    route = decision.get("route")

    return ChatResponse(
        assistant_id=request.assistant_id,
        session_id=session_id,
        response=response_text,
        route=route,
        fallback_reason=result.get("fallback_reason"),
        fallback_source=result.get("fallback_source"),
        rag_result=result.get("rag_result"),
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
