"""Langfuse: um trace por turno do grafo (nós, router, flows, RAG e LLM).

O CallbackHandler entra no `config` do `graph.invoke`; sessão, usuário e tags
vão como metadados `langfuse_*`. Sem chaves ou com LANGFUSE_ENABLED=false,
o config segue intacto.
"""

from __future__ import annotations

import logging
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from core import config

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = frozenset(
    {
        "cpf",
        "pis",
        "pispasepnit",
        "email",
        "nome",
        "nome_social",
        "data_nascimento",
        "datanascimento",
        "dtnasc",
        "datanasc",
    }
)
_MASK = "***"

_client: Langfuse | None = None


def mask_sensitive(*, data: Any, **_: Any) -> Any:
    """Troca valores de chaves com PII por `***` (recursivo, sem mutar a origem)."""
    if isinstance(data, dict):
        return {
            key: _MASK
            if isinstance(key, str) and key.lower() in _SENSITIVE_KEYS
            else mask_sensitive(data=value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive(data=item) for item in data]
    return data


def reset_langfuse_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.shutdown()
        except Exception:  # noqa: BLE001
            logger.debug("langfuse shutdown ignorado", exc_info=True)
    _client = None


def _get_client() -> Langfuse:
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
            environment=config.APP_ENV,
            mask=mask_sensitive,
        )
    return _client


def with_langfuse(
    run_config: dict[str, Any],
    *,
    assistant_id: str,
    session_id: str,
    user_id: str | None,
) -> dict[str, Any]:
    """Devolve cópia do `run_config` com callback e metadados Langfuse, se ativo."""
    if not config.is_langfuse_active():
        return run_config
    try:
        _get_client()
        handler = CallbackHandler(public_key=config.LANGFUSE_PUBLIC_KEY)
    except Exception:  # noqa: BLE001
        logger.exception("langfuse indisponivel session=%s", session_id)
        return run_config

    metadata: dict[str, Any] = {
        **(run_config.get("metadata") or {}),
        "langfuse_session_id": session_id,
        "langfuse_tags": ["the.ia", f"assistant:{assistant_id}"],
        "assistant_id": assistant_id,
    }
    if user_id:
        metadata["langfuse_user_id"] = user_id
    return {
        **run_config,
        "callbacks": [*(run_config.get("callbacks") or []), handler],
        "metadata": metadata,
    }


def flush_langfuse() -> None:
    if _client is None:
        return
    try:
        _client.flush()
    except Exception:  # noqa: BLE001
        logger.exception("langfuse flush falhou")
