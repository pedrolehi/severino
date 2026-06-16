from pathlib import Path
from enum import Enum

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from core.llm import llm
from graph.state import MultiAgentState
from tools import get_tools_catalog

PROMPT_PATH = Path(__file__).parent / "prompts" / "router_prompt.txt"


def load_prompt():
    with open(PROMPT_PATH, "r") as file:
        return file.read()


class Route(str, Enum):
    RAG = "rag"
    SERVICES = "services"
    FALLBACK = "fallback"


ROUTE_DESCRIPTIONS: dict[Route, str] = {
    Route.RAG: "RAG - busca em base de conhecimento",
    Route.SERVICES: "SERVICES - fluxos de serviços e consultas a sistemas de acordo com as capacidades listadas",
    Route.FALLBACK: "FALLBACK - conversa geral ou caso não haja capacidade compatível",
}


def get_route_catalog() -> str:
    return "\n".join(
        f"- {route.value.upper()}: {description}"
        for route, description in ROUTE_DESCRIPTIONS.items()
    )


class RouteDecision(BaseModel):
    intent: str = Field(
        description="A intenção do usuário na conversa com o peso maior no último input."
    )
    route: Route = Field(
        description="O roteamento para o agente deve ser baseado na intenção do usuário."
    )
    confidence: float = Field(
        ge=0, le=1, description="A confiança na decisão, de 0 a 1."
    )


structured_llm = llm.with_structured_output(RouteDecision)


def router_agent(state: MultiAgentState) -> dict:
    print(f"[ROUTER AGENT] Iniciando agente de roteamento...")

    system_prompt = load_prompt().format(
        routes=get_route_catalog(), capabilities=get_tools_catalog()
    )

    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history

    decision = structured_llm.invoke(messages)

    print(
        f"[ROUTER AGENT] intent={decision.intent}, route={decision.route}, confidence={decision.confidence}"
    )

    return {"decision": decision.model_dump()}
