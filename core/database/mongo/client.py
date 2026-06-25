import logging
import os
from typing import Optional

from core.config import MONGODB_DATABASE, MONGODB_URI

logger = logging.getLogger(__name__)

_client = None
_client_uri: Optional[str] = None


def is_mongo_configured() -> bool:
    return bool(MONGODB_URI)


def get_mongo_client():
    global _client, _client_uri

    if not MONGODB_URI:
        return None

    if _client is not None and _client_uri == MONGODB_URI:
        return _client

    try:
        from pymongo import MongoClient

        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _client_uri = MONGODB_URI
        _client.admin.command("ping")
        logger.info("MongoDB conectado (database=%s)", MONGODB_DATABASE)
        return _client
    except Exception as exc:
        logger.warning("MongoDB indisponível: %s", exc)
        _client = None
        _client_uri = None
        return None


def get_meta_collection(collection_name: str):
    client = get_mongo_client()
    if client is None:
        return None
    return client[MONGODB_DATABASE][collection_name]
