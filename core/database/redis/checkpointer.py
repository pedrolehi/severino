from langgraph.checkpoint.redis import RedisSaver
from core.database.redis.client import redis_client


def build_checkpointer():
    saver = RedisSaver(redis_client=redis_client)
    saver.setup()
    return saver
