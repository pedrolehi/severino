from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    content: str
    score: float
    metadata: dict


@dataclass(frozen=True, slots=True)
class RagRunResult:
    answer: str
    query: str
    collection_name: str
    chunks: tuple[RetrievedChunk, ...]


class VectorSearchPort(Protocol):
    def search(
        self,
        *,
        query: str,
        collection_name: str,
        top_k: int,
    ) -> list[RetrievedChunk]: ...
