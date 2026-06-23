from pathlib import Path

from langchain_core.messages import AIMessage, SystemMessage

from assistants.capabilities import resolve_capabilities
from core.llm import llm
from graph.state import MultiAgentState
from flows.registry import flow_name_from_tool

PROMPT_PATH = Path(__file__).parent / "prompts" / "service_caller_prompt.txt"


def load_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def service_caller_agent(state: MultiAgentState) -> dict:
    print("[TOOL CALLER AGENT] Iniciando agente de chamada de ferramentas...")

    assistant_id = state["assistant_id"]
    if not assistant_id:
        raise ValueError("Assistant ID não encontrado no estado")

    caps = resolve_capabilities(assistant_id)

    decision = state.get("decision") or {}
    intent = decision.get("intent", "Atender a solicitação do usuário")

    system_prompt = load_prompt().format(
        intent=intent, capabilities=caps.bindable_catalog()
    )

    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history

    response = llm.bind_tools(list(caps.bindable)).invoke(messages)

    if not response.tool_calls:
        return {"messages": [response]}

    tool_call = response.tool_calls[0]
    tool_name = tool_call["name"]

    flow_name = flow_name_from_tool(tool_name)

    if flow_name:
        if flow_name not in caps.flows_names:
            return {
                "messages": [
                    AIMessage(
                        content=f"O fluxo {flow_name} não existe ou não está disponível para o assistente {assistant_id}."
                    )
                ]
            }
        return {
            "service_target": flow_name,
            "active_flow": flow_name,
            "flow_step": None,
            "flow_data": None,
            "messages": [
                AIMessage(
                    content="",
                )
            ],
        }

    if tool_name in caps.tools_by_name:
        return {"service_target": None, "messages": [response]}

    return {
        "messages": [AIMessage(content="Não encontrei a ferramenta ou fluxo alvo.")]
    }
