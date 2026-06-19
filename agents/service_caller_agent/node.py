from pathlib import Path

from langchain_core.messages import AIMessage, SystemMessage

from core.llm import llm
from graph.state import MultiAgentState
from flows.registry import flow_name_from_tool
from tools import bindable_tools, get_bindagle_catalog, tools_dict


llm_with_tools = llm.bind_tools(bindable_tools)


PROMPT_PATH = Path(__file__).parent / "prompts" / "service_caller_prompt.txt"


def load_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def service_caller_agent(state: MultiAgentState) -> dict:

    print("[TOOL CALLER AGENT] Iniciando agente de chamada de ferramentas...")

    decision = state.get("decision") or {}
    intent = decision.get("intent", "Atender a solicitação do usuário")

    system_prompt = load_prompt().format(
        intent=intent, capabilities=get_bindagle_catalog()
    )

    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history

    response = llm_with_tools.invoke(messages)

    if not response.tool_calls:
        return {"messages": [response]}

    tool_call = response.tool_calls[0]
    tool_name = tool_call["name"]

    flow_name = flow_name_from_tool(tool_name)

    if flow_name:
        return {
            "service_target": flow_name,
            "messages": [
                AIMessage(
                    content="",
                )
            ],
        }

    if tool_name in tools_dict:
        return {"service_target": None, "messages": [response]}

    return {
        "messages": [AIMessage(content="Não encontrei a ferramenta ou fluxo alvo.")]
    }
