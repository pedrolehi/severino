from pathlib import Path
from enum import Enum

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from assistants.capabilities import resolve_capabilities
from core.llm import llm
from graph.state import MultiAgentState

PROMPT_PATH = Path(__file__).parent / "prompts" / "router_prompt.txt"


def load_prompt():
    with open(PROMPT_PATH, "r") as file:
        return file.read()


class Route(str, Enum):
    RAG = "rag"
    SERVICES = "services"
    FALLBACK = "fallback"


ROUTE_DESCRIPTIONS: dict[Route, str] = {
    Route.RAG: (
        "RAG - perguntas informativas (como fazer, políticas, procedimentos, documentação). "
        "Use quando o usuário quer saber/como proceder, sem tool ou flow correspondente."
    ),
    Route.SERVICES: (
        "SERVICES - executar ação via tool ou flow listada em capabilities "
        "(ex.: boleto, consulta de status)"
    ),
    Route.FALLBACK: (
        "FALLBACK - cumprimentos, conversa geral ou assunto fora do escopo "
        "(não é dúvida informativa nem serviço listado)"
    ),
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
    routing_reason: str = Field(
        description=(
            "Justificativa objetiva da rota escolhida: cite a mensagem do usuário. "
            "SERVICES: qual tool/flow do catálogo. "
            "RAG: por que é pergunta informativa/procedimento (mesmo sem tool). "
            "FALLBACK: por que não é informação nem serviço."
        ),
        min_length=10,
    )


structured_llm = llm.with_structured_output(RouteDecision)


def router_agent(state: MultiAgentState) -> dict:
    print("[ROUTER AGENT] Iniciando agente de roteamento...")
    assistant_id = state["assistant_id"]
    if not assistant_id:
        raise ValueError("Assistant ID não encontrado no estado")

    caps = resolve_capabilities(state["assistant_id"])
    system_prompt = load_prompt().format(
        routes=get_route_catalog(), capabilities=caps.router_catalog()
    )

    history = state["messages"][-20:]
    messages = [SystemMessage(content=system_prompt)] + history

    decision = structured_llm.invoke(messages)

    print(
        f"[ROUTER AGENT] intent={decision.intent}, route={decision.route}, "
        f"confidence={decision.confidence}, reason={decision.routing_reason}"
    )

    return {"decision": decision.model_dump()}
