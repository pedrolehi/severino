from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JudgeVerdictModel(BaseModel):
    action: Literal["accept", "retry_search", "fallback"]
    grounded: bool
    answers_question: bool
    confidence: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    rewritten_query: str | None = None
    retry_reason: str | None = None
    fallback_hint: str | None = None
