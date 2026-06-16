from pathlib import Path
from enum import Enum
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage, SystemMessage

from core.llm import llm
from flows.registry import get_flows_catalog, FLOW_BUILDERS
from tools import get_tools_catalog


class ServiceKind(str, Enum):
    TOLL = "tool"
    FLOW = "flow"
    NONE = "none"


class ServiceDecision(BaseModel):
    kind: ServiceKind = Field(
        description="Tipo de serviço: tool (1 turno), flow (multi-turno) ou none."
    )
    target: str = Field(description="Nome do serviço alvo: tool ou flow.")
    arguments: dict = Field(
        default_factory=dict,
        description="Argumentos da tool, Vazio se kind for flow ou none.",
    )


structured_llm = llm.with_structured_output(ServiceDecision)


PROMPT_PATH = Path(__file__).parent / "prompts" / "service_caller_prompt.txt"


def load_prompt() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def service_caller_agent(state: MultiAgentState) -> dict:

    print(f"[TOOL CALLER AGENT] Iniciando agente de chamada de ferramentas...")

    decision = state.get("decision") or {}
    intent = decision.get("intent", "Atender a solicitação do usuário")

    system_prompt = load_prompt().format(
        intent=intent, capabilities=get_tools_catalog(), flows=get_flows_catalog()
    )

    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history

    service = structured_llm.invoke(messages)

    if service.kind == ServiceKind.TOOL:
        return {
            "service_target": None,
            "messages": [
                AIMessage(
                    content="",
                )
            ],
        }
