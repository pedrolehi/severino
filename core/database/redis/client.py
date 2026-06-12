import redis
from core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD


def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        decode_responses=False,
        username="default",
        password=REDIS_PASSWORD,
    )


redis_client = get_redis_client()
