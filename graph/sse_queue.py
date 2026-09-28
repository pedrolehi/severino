from __future__ import annotations

from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


def push_sse(config: Optional[RunnableConfig], event: dict[str, Any]) -> None:
    """Empurra um evento SSE se a chamada veio de POST /chat/stream."""
    configurable = (config or {}).get("configurable") or {}
    sse_queue = configurable.get("token_queue")
    if sse_queue is None:
        return
    sse_queue.put(event)
