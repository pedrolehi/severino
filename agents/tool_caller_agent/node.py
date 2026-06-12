from pathlib import Path

from langchain_core.messages import SystemMessage

from core.llm import llm_with_tools
from graph.state import MultiAgentState
from tools import get_tools_catalog

PROMPT_PATH = Path(__file__).parent / "prompts" / "tool_caller_prompt.txt"


def load_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def tool_caller_agent(state: MultiAgentState) -> dict:

    print(f"[TOOL CALLER AGENT] Iniciando agente de chamada de ferramentas...")

    decision = state.get("decision") or {}
    intent = decision.get("intent", "Atender a solicitação do usuário")

    system_prompt = load_prompt().format(
        intent=intent, capabilities=get_tools_catalog()
    )

    history = state["messages"][-5:]
    messages = [SystemMessage(content=system_prompt)] + history

    response = llm_with_tools.invoke(messages)

    print(f"[TOOL CALLER AGENT] response={getattr(response, 'tool_calls', None)}")

    return {"messages": [response]}
