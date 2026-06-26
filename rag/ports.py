from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    content: str
    score: float
    metadata: dict
    similarity: float


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    top_score: float
    top_similarity: float
    chunk_count: int
    collection_name: str
    search_query: str
    search_attempt: int


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
