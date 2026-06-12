from core.database.redis.checkpointer import build_checkpointer

memory = build_checkpointer()


def get_memory():
    return memory
