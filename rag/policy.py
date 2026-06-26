from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

from assistants.assistant_contract import AssistantRegistration, RagBinding
from rag.config import RAG_ENABLE_RERANKING, RAG_TOP_K

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PROMPT = Path(__file__).parent / "prompts" / "default.txt"
DEFAULT_JUDGE_PROMPT = Path(__file__).parent / "prompts" / "judge.txt"
DEFAULT_FALLBACK_PROMPT = Path(__file__).parent / "prompts" / "fallback.txt"


@dataclass(frozen=True, slots=True)
class SearchPolicy:
    top_k: int = RAG_TOP_K
    search_buffer: int = 3
    enable_reranking: bool = RAG_ENABLE_RERANKING
    reranker_mode: str = "dedicated"
    use_hybrid_search: bool = True
    enable_query_expansion: bool = False


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    min_similarity: float = 0.35
    max_search_attempts: int = 2
    judge_enabled: bool = True
    allow_judge_retry: bool = True


@dataclass(frozen=True, slots=True)
class RagPolicy:
    project_id: str
    prompt_path: Path = DEFAULT_PROMPT
    judge_prompt_path: Path = DEFAULT_JUDGE_PROMPT
    fallback_prompt_path: Path = DEFAULT_FALLBACK_PROMPT
    search: SearchPolicy = field(default_factory=SearchPolicy)
    quality: QualityPolicy = field(default_factory=QualityPolicy)


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    if value is None:
        return default
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def resolve_rag_policy(assistant: AssistantRegistration) -> RagPolicy:
    binding: RagBinding = assistant.rag
    base = RagPolicy(project_id=binding.project_id)

    overrides: dict = {}
    if binding.prompt_path is not None:
        overrides["prompt_path"] = _resolve_path(binding.prompt_path, DEFAULT_PROMPT)
    if binding.judge_prompt_path is not None:
        overrides["judge_prompt_path"] = _resolve_path(
            binding.judge_prompt_path,
            DEFAULT_JUDGE_PROMPT,
        )
    if binding.fallback_prompt_path is not None:
        overrides["fallback_prompt_path"] = _resolve_path(
            binding.fallback_prompt_path,
            DEFAULT_FALLBACK_PROMPT,
        )

    search = base.search
    if binding.search_top_k is not None:
        search = replace(search, top_k=binding.search_top_k)
    if binding.search_buffer is not None:
        search = replace(search, search_buffer=binding.search_buffer)
    if binding.use_hybrid_search is not None:
        search = replace(search, use_hybrid_search=binding.use_hybrid_search)

    quality = base.quality
    if binding.max_search_attempts is not None:
        quality = replace(quality, max_search_attempts=binding.max_search_attempts)
    if binding.min_similarity is not None:
        quality = replace(quality, min_similarity=binding.min_similarity)

    return replace(base, search=search, quality=quality, **overrides)
