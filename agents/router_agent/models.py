from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Route(str, Enum):
    RAG = "rag"
    SERVICES = "services"
    FALLBACK = "fallback"


ROUTE_DESCRIPTIONS: dict[Route, str] = {
    Route.RAG: (
        "RAG - perguntas informativas (políticas, procedimentos, documentação). "
        "Use quando NÃO houver tool ou flow em capabilities para a ação pedida."
    ),
    Route.SERVICES: (
        "SERVICES - iniciar ou executar tool/flow listada em capabilities. "
        "Inclui 'como emitir', 'como solicitar', 'quero a segunda via' quando o tema "
        "bate com um flow (ex.: nota fiscal, boleto)."
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


class ChoiceTrace(BaseModel):
    """Espelha answer OpenJEV choice (debug/métricas)."""

    type: str = "choice"
    choice: str
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)


class RouteDecision(BaseModel):
    """Schema LLM structured + campos de controle do grafo."""

    route: Route = Field(
        description="Roteamento baseado na intenção do usuário."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confiança da rota escolhida (0..1). Usar para métricas.",
    )


def build_choice_trace(
    *,
    choice: str,
    confidence: float,
    probabilities: dict[str, float] | None = None,
) -> ChoiceTrace:
    probs = dict(probabilities or {})
    if not probs:
        probs = {choice: confidence}
    return ChoiceTrace(
        type="choice",
        choice=choice,
        probabilities=probs,
        confidence=max(0.0, min(1.0, confidence)),
    )


def decision_to_payload(
    decision: RouteDecision,
    *,
    source: str,
    choice_trace: ChoiceTrace | None = None,
) -> dict[str, Any]:
    """Payload do state: route flat + trace estilo OpenJEV."""
    trace = choice_trace or build_choice_trace(
        choice=decision.route.value,
        confidence=decision.confidence,
    )
    return {
        "route": decision.route.value,
        "confidence": decision.confidence,
        "source": source,
        "trace": {
            "route": trace.model_dump(mode="json"),
        },
    }
