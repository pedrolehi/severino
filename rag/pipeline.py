from __future__ import annotations

from assistants.assistant_contract import AssistantRegistration
from assistants.registry import get_assistant_by_id
from rag.ports import RagRunResult, RetrievedChunk
from rag.subgraph.builder import build_rag_subgraph

_rag_subgraph = build_rag_subgraph()


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(nenhum trecho encontrado)"

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        filename = chunk.metadata.get("filename") or chunk.metadata.get("document_id") or "—"
        parts.append(
            f"[{index}] (score={chunk.score:.3f}, sim={chunk.similarity:.2f}, arquivo={filename})\n"
            f"{chunk.content.strip()}"
        )
    return "\n\n".join(parts)


def format_chunks_debug(
    chunks: list[RetrievedChunk],
    *,
    collection_name: str,
    truncate: int | None = None,
) -> str:
    lines = [
        "",
        f"--- Chunks ({len(chunks)}) | collection={collection_name} ---",
    ]
    for index, chunk in enumerate(chunks, start=1):
        filename = chunk.metadata.get("filename") or chunk.metadata.get("document_id") or "—"
        content = chunk.content.strip()
        if truncate is not None and len(content) > truncate:
            content = f"{content[:truncate]}…"

        lines.append(
            f"[{index}] sim={chunk.similarity:.2f} score={chunk.score:.3f} | "
            f"id={chunk.id} | arquivo={filename}"
        )
        lines.append(content)
        lines.append("")

    lines.append("--- fim chunks ---")
    return "\n".join(lines)


def _chunk_from_dict(data: dict) -> RetrievedChunk:
    return RetrievedChunk(
        id=str(data.get("id", "")),
        content=str(data.get("content", "")),
        score=float(data.get("score", 0)),
        metadata=dict(data.get("metadata") or {}),
        similarity=float(data.get("similarity", 0)),
    )


def run_rag_subgraph(
    *,
    assistant_id: str,
    query: str,
) -> dict:
    return _rag_subgraph.invoke(
        {
            "assistant_id": assistant_id,
            "query": query.strip(),
        }
    )


def run_rag(
    *,
    assistant: AssistantRegistration,
    query: str,
    app_env: str | None = None,
) -> RagRunResult:
    del app_env  # resolvido via APP_ENV em project_store
    final_state = run_rag_subgraph(assistant_id=assistant.id, query=query)

    if final_state.get("fallback_reason"):
        raise RagFallbackError(
            reason=str(final_state.get("fallback_reason")),
            source=str(final_state.get("fallback_source") or "rag"),
            hint=final_state.get("fallback_hint"),
            state=final_state,
        )

    rag_result = final_state.get("rag_result") or {}
    chunks = tuple(
        _chunk_from_dict(item) for item in (final_state.get("chunks") or [])
    )
    return RagRunResult(
        answer=str(rag_result.get("answer") or ""),
        query=query.strip(),
        collection_name=str(
            rag_result.get("collection_name")
            or final_state.get("collection_name")
            or ""
        ),
        chunks=chunks,
        search_attempts=int(rag_result.get("search_attempts") or 1),
        judge_action=rag_result.get("judge_action"),
        retrieval_metrics=rag_result.get("retrieval_metrics"),
    )


class RagFallbackError(Exception):
    def __init__(
        self,
        *,
        reason: str,
        source: str,
        hint: str | None,
        state: dict,
    ) -> None:
        self.reason = reason
        self.source = source
        self.hint = hint
        self.state = state
        super().__init__(reason)


def run_rag_for_assistant_id(
    *,
    assistant_id: str,
    query: str,
    app_env: str | None = None,
) -> RagRunResult:
    assistant = get_assistant_by_id(assistant_id)
    return run_rag(assistant=assistant, query=query, app_env=app_env)
