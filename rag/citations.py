from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from core.config import SEARCH_VECTORY_URL
from rag.ports import RetrievedChunk

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def _chunk_filename(metadata: dict[str, Any]) -> str | None:
    filename = metadata.get("filename") or metadata.get("document_id")
    return str(filename) if filename else None


def _chunk_document_path(metadata: dict[str, Any]) -> str | None:
    document_source = metadata.get("document_source")
    if isinstance(document_source, dict):
        download_path = document_source.get("download_cos_path")
        if download_path:
            return str(download_path)
        cos_path = document_source.get("cos_path")
        if cos_path:
            return str(cos_path)

    filename = _chunk_filename(metadata)
    if filename:
        return filename.replace("\\", "/").lstrip("/")
    return None


def build_document_download_url(cos_path: str | None) -> str | None:
    if not cos_path:
        return None

    normalized = cos_path.replace("\\", "/").lstrip("/")
    if not normalized:
        return None

    root = SEARCH_VECTORY_URL.rstrip("/")
    encoded_path = quote(normalized, safe="/")
    return f"{root}/cos/documents/download?path={encoded_path}"


def chunk_to_citation_payload(chunk: RetrievedChunk, *, index: int) -> dict[str, Any]:
    metadata = dict(chunk.metadata or {})
    document_path = _chunk_document_path(metadata)
    return {
        "index": index,
        "id": chunk.id,
        "content": chunk.content,
        "filename": _chunk_filename(metadata),
        "document_path": document_path,
        "document_url": build_document_download_url(document_path),
        "similarity": chunk.similarity,
    }


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
                "chunk": chunk_to_citation_payload(chunk, index=chunk_index),
            }
        )

    return citations
