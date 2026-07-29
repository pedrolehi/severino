import redis
from core.config import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, is_redis_configured


def get_redis_client():
    if not is_redis_configured():
        raise ValueError("Redis não configurado (REDIS_HOST/PORT/PASSWORD).")
    return redis.Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        decode_responses=False,
        username="default",
        password=REDIS_PASSWORD,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
