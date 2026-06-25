from langchain_core.messages import AIMessage, HumanMessage

from graph.state import MultiAgentState
from rag.pipeline import run_rag_for_assistant_id


def rag_agent(state: MultiAgentState) -> dict:
    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id não encontrado no estado")

    last_message = state["messages"][-1]
    if not isinstance(last_message, HumanMessage):
        raise ValueError("Última mensagem deve ser do usuário para RAG")

    query = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
    print(f"[RAG Agent] assistant={assistant_id}, query={query[:80]!r}...")

    result = run_rag_for_assistant_id(assistant_id=assistant_id, query=query)
    return {"messages": [AIMessage(content=result.answer)]}


def fallback_agent(state: MultiAgentState):
    print("[Fallback Agent] Respondendo com fallback...")
    return {"messages": [AIMessage(content="Fallback Agent: Respondendo com fallback")]}
