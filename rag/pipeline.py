from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from assistants.assistant_contract import AssistantRegistration
from assistants.registry import get_assistant_by_id
from core.config import APP_ENV
from core.llm import llm
from rag.adapters.search_vectory import SearchVectoryAdapter
from rag.config import RAG_TOP_K
from rag.ports import RagRunResult, RetrievedChunk
from rag.project_store import resolve_collection_name

PROMPT_PATH = Path(__file__).parent / "prompts" / "default.txt"
_search_adapter = SearchVectoryAdapter()


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(nenhum trecho encontrado)"

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        filename = chunk.metadata.get("filename") or chunk.metadata.get("document_id") or "—"
        parts.append(
            f"[{index}] (score={chunk.score:.3f}, arquivo={filename})\n{chunk.content.strip()}"
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
        chunk_id = chunk.id or "—"
        content = chunk.content.strip()
        if truncate is not None and len(content) > truncate:
            content = f"{content[:truncate]}…"

        lines.append(f"[{index}] score={chunk.score:.3f} | id={chunk_id} | arquivo={filename}")
        lines.append(content)
        lines.append("")

    lines.append("--- fim chunks ---")
    return "\n".join(lines)


def run_rag(
    *,
    assistant: AssistantRegistration,
    query: str,
    app_env: str | None = None,
) -> RagRunResult:
    env = app_env or APP_ENV
    collection_name = resolve_collection_name(assistant.rag.project_id, env)
    chunks = _search_adapter.search(
        query=query,
        collection_name=collection_name,
        top_k=RAG_TOP_K,
    )
    prompt = load_prompt_template().format(
        context=format_context(chunks),
        query=query.strip(),
    )
    response = llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=query),
        ]
    )
    content = response.content
    answer = content if isinstance(content, str) else str(content)
    return RagRunResult(
        answer=answer,
        query=query.strip(),
        collection_name=collection_name,
        chunks=tuple(chunks),
    )


def run_rag_for_assistant_id(
    *,
    assistant_id: str,
    query: str,
    app_env: str | None = None,
) -> RagRunResult:
    assistant = get_assistant_by_id(assistant_id)
    return run_rag(assistant=assistant, query=query, app_env=app_env)
