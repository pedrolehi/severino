from __future__ import annotations

import re
from typing import Any

from rag.ports import RetrievedChunk

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def chunk_source_payload(chunk: RetrievedChunk) -> dict[str, Any]:
    if chunk.source:
        return dict(chunk.source)
    return {
        "id": chunk.id,
        "content": chunk.content,
        "score": chunk.distance,
        "distance": chunk.distance,
        "adjusted_score": chunk.adjusted_score,
        "similarity": chunk.similarity,
        "metadata": dict(chunk.metadata or {}),
    }


def chunks_to_retrieval_payload(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [chunk_source_payload(chunk) for chunk in chunks]


def find_marker_positions(answer: str) -> dict[int, list[int]]:
    positions: dict[int, list[int]] = {}
    for match in _CITATION_PATTERN.finditer(answer):
        chunk_index = int(match.group(1))
        positions.setdefault(chunk_index, []).append(match.start())
    return positions


def parse_cited_chunk_indices(answer: str) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for match in _CITATION_PATTERN.finditer(answer):
        index = int(match.group(1))
        if index not in seen:
            seen.add(index)
            ordered.append(index)
    return ordered


def build_citations(
    answer: str,
    chunks: list[RetrievedChunk],
) -> list[dict[str, Any]]:
    if not chunks:
        return []

    positions_by_index = find_marker_positions(answer)
    cited_indices = parse_cited_chunk_indices(answer)
    citations: list[dict[str, Any]] = []

    for chunk_index in cited_indices:
        if chunk_index < 1 or chunk_index > len(chunks):
            continue

        chunk = chunks[chunk_index - 1]
        citations.append(
            {
                "marker": f"[{chunk_index}]",
                "positions": positions_by_index.get(chunk_index, []),
                "chunk": chunk_source_payload(chunk),
            }
        )

    return citations
