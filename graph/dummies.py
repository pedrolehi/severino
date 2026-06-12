from graph.state import MultiAgentState
from langchain_core.messages import AIMessage


def rag_agent(state: MultiAgentState):
    print("[RAG Agent] Iniciando busca...")
    return {
        "messages": [AIMessage(content="RAG Agent: Buscou e retornou as informações")]
    }


def fallback_agent(state: MultiAgentState):
    print("[Fallback Agent] Respondendo com fallback...")
    return {"messages": [AIMessage(content="Fallback Agent: Respondendo com fallback")]}
