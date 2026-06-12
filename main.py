import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
from langchain_core.messages import HumanMessage
from graph.builder import app_graph


class AgentContext(BaseModel):
    user_id: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    message: str
    context: AgentContext | None = None


app = FastAPI(title="Meu multiagent API")


@app.get("/")
def read_root():
    return {"message": "Health check ok!"}


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    user_msg = request.message
    user_id = request.context.user_id if request.context else None
    session_id = request.context.session_id if request.context else None

    config = {"configurable": {"thread_id": session_id}}

    initial_state = {"messages": [HumanMessage(content=user_msg)], "user_id": user_id}

    print(f"Iniciando o fluxo com o estado inicial: {initial_state}")
    result = app_graph.invoke(initial_state, config=config)

    final_message = result["messages"][-1].content

    return {"agent": "Chat Agent", "response": final_message}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
