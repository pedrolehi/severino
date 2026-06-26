from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from assistants.registry import get_assistant_by_id
from core.config import APP_ENV
from core.llm import llm
from rag.adapters.search_vectory import SearchVectoryAdapter
from rag.policy import RagPolicy, resolve_rag_policy
from rag.citations import build_citations
from rag.ports import RagRunResult, RetrievedChunk
from rag.project_store import resolve_collection_name
from rag.scoring import passes_similarity_threshold
from rag.subgraph.models import JudgeVerdictModel
from rag.subgraph.state import RagSubgraphState

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_search_adapter = SearchVectoryAdapter()
_judge_llm = llm.with_structured_output(JudgeVerdictModel)


def _load_policy(state: RagSubgraphState) -> RagPolicy:
    assistant_id = state.get("assistant_id")
    if not assistant_id:
        raise ValueError("assistant_id ausente no state do subgrafo RAG")
    return resolve_rag_policy(get_assistant_by_id(assistant_id))


def _chunk_to_dict(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "content": chunk.content,
        "score": chunk.score,
        "similarity": chunk.similarity,
        "metadata": chunk.metadata,
    }


def _chunk_from_dict(data: dict[str, Any]) -> RetrievedChunk:
    return RetrievedChunk(
        id=str(data.get("id", "")),
        content=str(data.get("content", "")),
        score=float(data.get("score", 0)),
        metadata=dict(data.get("metadata") or {}),
        similarity=float(data.get("similarity", 0)),
    )


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(nenhum trecho encontrado)"

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        filename = (
            chunk.metadata.get("filename")
            or chunk.metadata.get("document_id")
            or "—"
        )
        parts.append(
            f"[{index}] (id={chunk.id}, sim={chunk.similarity:.2f}, arquivo={filename})\n"
            f"{chunk.content.strip()}"
        )
    return "\n\n".join(parts)


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def prepare_query(state: RagSubgraphState) -> dict[str, Any]:
    query = (state.get("query") or "").strip()
    if not query:
        raise ValueError("query ausente no state do subgrafo RAG")

    return {
        "search_query": query,
        "search_attempt": 0,
        "search_history": [],
        "fallback_reason": None,
        "fallback_source": None,
        "fallback_hint": None,
    }


def retrieve(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    collection_name = resolve_collection_name(policy.project_id, APP_ENV)
    search_query = (state.get("search_query") or state.get("query") or "").strip()
    attempt = int(state.get("search_attempt") or 0)

    chunks = _search_adapter.search(
        query=search_query,
        collection_name=collection_name,
        search_policy=policy.search,
    )

    history = list(state.get("search_history") or [])
    top_score = chunks[0].score if chunks else 1.0
    top_similarity = chunks[0].similarity if chunks else 0.0
    history.append(
        {
            "attempt": attempt,
            "search_query": search_query,
            "top_score": top_score,
            "top_similarity": top_similarity,
            "chunk_count": len(chunks),
            "chunk_ids": [chunk.id for chunk in chunks[:5]],
        }
    )

    metrics = {
        "top_score": top_score,
        "top_similarity": top_similarity,
        "chunk_count": len(chunks),
        "collection_name": collection_name,
        "search_query": search_query,
        "search_attempt": attempt,
    }

    return {
        "collection_name": collection_name,
        "chunks": [_chunk_to_dict(chunk) for chunk in chunks],
        "retrieval_metrics": metrics,
        "search_history": history,
    }


def retrieval_gate(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    chunks = [_chunk_from_dict(item) for item in (state.get("chunks") or [])]
    attempt = int(state.get("search_attempt") or 0)
    max_attempts = policy.quality.max_search_attempts

    if not chunks:
        if attempt + 1 < max_attempts:
            return {
                "retry_reason": "Nenhum trecho encontrado na busca.",
                "judge_verdict": {
                    "action": "retry_search",
                    "rewritten_query": None,
                },
            }
        return {
            "fallback_reason": "rag_retrieval:no_results",
            "fallback_source": "rag_retrieval",
            "fallback_hint": "Não há trechos indexados para esta pergunta.",
        }

    top = chunks[0]
    if not passes_similarity_threshold(top.score, policy.quality.min_similarity):
        if attempt + 1 < max_attempts:
            return {
                "retry_reason": (
                    f"Similaridade baixa ({top.similarity:.2f} < "
                    f"{policy.quality.min_similarity:.2f})."
                ),
                "judge_verdict": {
                    "action": "retry_search",
                    "rewritten_query": None,
                },
            }
        return {
            "fallback_reason": "rag_retrieval:low_similarity",
            "fallback_source": "rag_retrieval",
            "fallback_hint": (
                "Os trechos recuperados não parecem relevantes o suficiente."
            ),
        }

    return {"retry_reason": None, "judge_verdict": None}


def route_after_retrieval_gate_node(state: RagSubgraphState) -> str:
    if state.get("fallback_reason"):
        return "end_fallback"
    verdict = state.get("judge_verdict") or {}
    if verdict.get("action") == "retry_search":
        return "rewrite_query"
    return "build_context"


def build_context(state: RagSubgraphState) -> dict[str, Any]:
    chunks = [_chunk_from_dict(item) for item in (state.get("chunks") or [])]
    return {
        "context_text": _format_context(chunks),
        "judge_verdict": None,
    }


def generate(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    query = (state.get("query") or "").strip()
    context = state.get("context_text") or "(nenhum trecho encontrado)"
    prompt_template = _read_prompt(policy.prompt_path)
    prompt = prompt_template.format(context=context, query=query)

    response = llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=query),
        ]
    )
    content = response.content
    answer = content if isinstance(content, str) else str(content)
    return {"draft_answer": answer}


def judge(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    if not policy.quality.judge_enabled:
        return {
            "judge_verdict": {
                "action": "accept",
                "grounded": True,
                "answers_question": True,
                "confidence": 1.0,
                "issues": [],
            }
        }

    attempt = int(state.get("search_attempt") or 0)
    max_attempts = policy.quality.max_search_attempts
    can_retry = (
        policy.quality.allow_judge_retry and (attempt + 1) < max_attempts
    )

    prompt_template = _read_prompt(policy.judge_prompt_path)
    prompt = prompt_template.format(
        query=(state.get("query") or "").strip(),
        context=state.get("context_text") or "",
        answer=state.get("draft_answer") or "",
        search_attempt=attempt + 1,
        max_attempts=max_attempts,
    )

    verdict = _judge_llm.invoke([SystemMessage(content=prompt)])

    if verdict.action == "retry_search" and not can_retry:
        verdict = verdict.model_copy(
            update={
                "action": "fallback",
                "fallback_hint": verdict.fallback_hint
                or "Esgotadas as tentativas de busca.",
            }
        )

    if verdict.action == "retry_search" and not verdict.rewritten_query:
        verdict = verdict.model_copy(
            update={
                "retry_reason": verdict.retry_reason
                or "A resposta não ficou bem sustentada nos trechos.",
            }
        )

    result: dict[str, Any] = {"judge_verdict": verdict.model_dump()}
    if verdict.action == "fallback":
        result.update(
            {
                "fallback_reason": "rag_judge:"
                + ("ungrounded" if not verdict.grounded else "low_quality"),
                "fallback_source": "rag_judge",
                "fallback_hint": verdict.fallback_hint,
            }
        )
    elif verdict.action == "retry_search":
        result["retry_reason"] = verdict.retry_reason

    return result


def rewrite_query(state: RagSubgraphState) -> dict[str, Any]:
    policy = _load_policy(state)
    attempt = int(state.get("search_attempt") or 0) + 1
    previous_query = (state.get("search_query") or state.get("query") or "").strip()
    verdict = state.get("judge_verdict") or {}
    retry_reason = (
        state.get("retry_reason")
        or verdict.get("retry_reason")
        or "Melhorar cobertura da busca."
    )
    rewritten = (verdict.get("rewritten_query") or "").strip()

    if not rewritten:
        rewrite_template = _read_prompt(PROMPTS_DIR / "rewrite.txt")
        rewrite_prompt = rewrite_template.format(
            retry_reason=retry_reason,
            previous_query=previous_query,
        )
        response = llm.invoke([HumanMessage(content=rewrite_prompt)])
        content = response.content
        rewritten = (content if isinstance(content, str) else str(content)).strip()

    if rewritten.lower() == previous_query.lower():
        rewritten = f"{previous_query} procedimento documentação"

    return {
        "search_query": rewritten,
        "search_attempt": attempt,
        "judge_verdict": None,
        "draft_answer": None,
        "fallback_reason": None,
        "fallback_source": None,
        "fallback_hint": None,
        "chunks": [],
    }


def pack_response(state: RagSubgraphState) -> dict[str, Any]:
    chunks = tuple(
        _chunk_from_dict(item) for item in (state.get("chunks") or [])
    )
    attempt = int(state.get("search_attempt") or 0) + 1
    verdict = state.get("judge_verdict") or {}

    result = RagRunResult(
        answer=state.get("draft_answer") or "",
        query=(state.get("query") or "").strip(),
        collection_name=state.get("collection_name") or "",
        chunks=chunks,
        search_attempts=attempt,
        judge_action=str(verdict.get("action")) if verdict else None,
        retrieval_metrics=state.get("retrieval_metrics"),
    )
    citations = build_citations(result.answer, list(chunks))

    from langchain_core.messages import AIMessage

    return {
        "rag_result": {
            "query": result.query,
            "collection_name": result.collection_name,
            "search_attempts": result.search_attempts,
            "judge_action": result.judge_action,
            "retrieval_metrics": result.retrieval_metrics,
            "retrieved_chunk_count": len(result.chunks),
            "citations": citations,
        },
        "messages": [AIMessage(content=result.answer)],
    }


def mark_fallback(state: RagSubgraphState) -> dict[str, Any]:
    if state.get("fallback_reason"):
        return {}
    return {
        "fallback_reason": "rag_retrieval:unknown",
        "fallback_source": "rag_retrieval",
    }
