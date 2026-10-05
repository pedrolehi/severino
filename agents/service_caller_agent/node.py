from pathlib import Path

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from assistants.capabilities import resolve_capabilities
from core.llm import llm
from flows.registry import flow_name_from_tool
from graph.sse_queue import push_sse
from graph.state import MultiAgentState

PROMPT_PATH = Path(__file__).parent / "prompts" / "service_caller_prompt.txt"


def load_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def service_caller_agent(
    state: MultiAgentState, config: RunnableConfig | None = None
) -> dict:
    print("[TOOL CALLER AGENT] Iniciando agente de chamada de ferramentas...")
    push_sse(config, {"event": "step", "id": "service_caller", "status": "running"})

    assistant_id = state["assistant_id"]
    if not assistant_id:
        raise ValueError("Assistant ID não encontrado no estado")

    caps = resolve_capabilities(assistant_id)

    system_prompt = load_prompt().format(capabilities=caps.bindable_catalog())

    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history

    response = llm.bind_tools(list(caps.bindable)).invoke(messages)
    push_sse(config, {"event": "step", "id": "service_caller", "status": "ok"})
    if response.tool_calls:
        response = AIMessage(
            content="",
            tool_calls=response.tool_calls,
            id=response.id,
        )

    if not response.tool_calls:
        return {"service_target": None, "messages": [response]}

    tool_call = response.tool_calls[0]
    tool_name = tool_call["name"]
    print(f"[TOOL CALLER AGENT] tool={tool_name}", flush=True)

    flow_name = flow_name_from_tool(tool_name)

    if flow_name:
        if flow_name not in caps.flow_names:
            return {
                "service_target": None,
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
        "service_target": None,
        "messages": [AIMessage(content="Não encontrei a ferramenta ou fluxo alvo.")],
    }
