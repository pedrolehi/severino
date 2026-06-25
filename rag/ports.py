from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    content: str
    score: float
    metadata: dict


class VectorSearchPort(Protocol):
    def search(
        self,
        *,
        query: str,
        collection_name: str,
        top_k: int,
    ) -> list[RetrievedChunk]: ...
