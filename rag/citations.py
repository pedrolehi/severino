from __future__ import annotations

import re
from typing import Any

from rag.ports import RetrievedChunk

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")
_EXCERPT_MAX_LEN = 400


def _chunk_filename(metadata: dict[str, Any]) -> str | None:
    filename = metadata.get("filename") or metadata.get("document_id")
    return str(filename) if filename else None


def _chunk_download_path(metadata: dict[str, Any]) -> str | None:
    document_source = metadata.get("document_source")
    if isinstance(document_source, dict):
        download_path = document_source.get("download_cos_path")
        if download_path:
            return str(download_path)
        cos_path = document_source.get("cos_path")
        if cos_path:
            return str(cos_path)
    return None


def chunk_to_payload(chunk: RetrievedChunk, *, index: int) -> dict[str, Any]:
    metadata = dict(chunk.metadata or {})
    return {
        "index": index,
        "id": chunk.id,
        "content": chunk.content,
        "score": chunk.score,
        "similarity": chunk.similarity,
        "filename": _chunk_filename(metadata),
        "download_cos_path": _chunk_download_path(metadata),
        "metadata": metadata,
    }


def chunks_to_payloads(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [chunk_to_payload(chunk, index=index) for index, chunk in enumerate(chunks, start=1)]


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
    *,
    excerpt_max_len: int = _EXCERPT_MAX_LEN,
) -> list[dict[str, Any]]:
    if not chunks:
        return []

    positions_by_index = find_marker_positions(answer)
    cited_indices = parse_cited_chunk_indices(answer)

    if not cited_indices:
        cited_indices = list(range(1, min(len(chunks), 3) + 1))

    citations: list[dict[str, Any]] = []
    for chunk_index in cited_indices:
        if chunk_index < 1 or chunk_index > len(chunks):
            continue

        chunk = chunks[chunk_index - 1]
        metadata = dict(chunk.metadata or {})
        excerpt = chunk.content.strip()
        if len(excerpt) > excerpt_max_len:
            excerpt = f"{excerpt[:excerpt_max_len]}…"

        citations.append(
            {
                "marker": f"[{chunk_index}]",
                "chunk_index": chunk_index,
                "chunk_id": chunk.id,
                "filename": _chunk_filename(metadata),
                "download_cos_path": _chunk_download_path(metadata),
                "excerpt": excerpt,
                "score": chunk.score,
                "similarity": chunk.similarity,
                "positions": positions_by_index.get(chunk_index, []),
            }
        )

    return citations
