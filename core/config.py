import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

APP_ENV = (os.getenv("APP_ENV") or "dev").strip().lower()
SEARCH_VECTORY_URL = (
    os.getenv("SEARCH_VECTORY_URL") or "http://localhost:8081/api/v1"
).strip()
# S2S com search-vectory (header X-Internal-Token). Mesmo valor de INTERNAL_API_TOKEN.
SEARCH_VECTORY_INTERNAL_TOKEN = (
    os.getenv("SEARCH_VECTORY_INTERNAL_TOKEN")
    or os.getenv("INTERNAL_API_TOKEN")
    or ""
).strip() or None
MONGODB_URI = (os.getenv("MONGODB_URI") or "").strip()
MONGODB_DATABASE = (os.getenv("MONGODB_DATABASE") or "vectory").strip() or "vectory"

REDIS_HOST = (os.getenv("REDIS_HOST") or "").strip()
REDIS_PORT = (os.getenv("REDIS_PORT") or "").strip()
REDIS_PASSWORD = (os.getenv("REDIS_PASSWORD") or "").strip()

# OpenJEV (router e demais decisões tipadas)
OPENJEV_BASE_URL = (
    os.getenv("OPENJEV_BASE_URL") or "http://172.23.130.84:5000"
).strip().rstrip("/")
OPENJEV_API_KEY = (os.getenv("OPENJEV_API_KEY") or "").strip() or None
OPENJEV_TIMEOUT_S = float(os.getenv("OPENJEV_TIMEOUT_S") or "30")
USE_JEV_ROUTER = (os.getenv("USE_JEV_ROUTER") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
}


def is_redis_configured() -> bool:
    return bool(REDIS_HOST and REDIS_PORT and REDIS_PASSWORD)


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não está configurado")
