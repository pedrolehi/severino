from langgraph.checkpoint.redis import RedisSaver

from core.database.redis.client import get_redis_client


def build_redis_checkpointer():
    redis_client = get_redis_client()
    redis_client.ping()
    saver = RedisSaver(redis_client=redis_client)
    saver.setup()
    return saver
