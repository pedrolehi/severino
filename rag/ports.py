from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    content: str
    distance: float  # distância L2 Milvus (menor = melhor)
    metadata: dict
    similarity: float  # uso interno (gate/contexto)
    adjusted_score: float | None = None  # pós-rerank vectory (menor = melhor)
    source: dict[str, Any] | None = None  # item bruto do search-vectory

    @property
    def score(self) -> float:
        """Distância efetiva para gate: rerank quando existir."""
        if self.adjusted_score is not None:
            return self.adjusted_score
        return self.distance


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    top_distance: float
    top_similarity: float


@dataclass(frozen=True, slots=True)
class RagRunResult:
    answer: str
    query: str
    collection_name: str
    chunks: tuple[RetrievedChunk, ...]
    search_attempts: int = 1
    judge_action: str | None = None
    retrieval_metrics: dict[str, Any] | None = None


FallbackSource = Literal["router", "rag_retrieval", "rag_judge"]


@dataclass(frozen=True, slots=True)
class RagJudgeVerdict:
    action: Literal["accept", "retry_search", "fallback"]
    grounded: bool
    answers_question: bool
    confidence: float
    issues: tuple[str, ...]
    rewritten_query: str | None = None
    retry_reason: str | None = None
    fallback_hint: str | None = None


class VectorSearchPort(Protocol):
    def search(
        self,
        *,
        query: str,
        collection_name: str,
        search_policy: Any,
    ) -> list[RetrievedChunk]: ...
