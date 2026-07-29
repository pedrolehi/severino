import logging

from langgraph.checkpoint.memory import InMemorySaver
from redis.exceptions import RedisError

from core.config import is_redis_configured
from core.database.redis.checkpointer import build_redis_checkpointer

logger = logging.getLogger(__name__)


def build_checkpointer():
    if is_redis_configured():
        try:
            saver = build_redis_checkpointer()
            logger.info("Checkpointer ativo: Redis")
            return saver
        except (OSError, TimeoutError, ValueError, RedisError) as exc:
            logger.warning(
                "Redis indisponível (%s). Fallback para InMemorySaver.",
                exc,
            )
    else:
        logger.warning("Redis não configurado. Usando InMemorySaver.")

    return InMemorySaver()


memory = build_checkpointer()


def get_memory():
    return memory
