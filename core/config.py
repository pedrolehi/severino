import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

APP_ENV = (os.getenv("APP_ENV") or "dev").strip().lower()
SEARCH_VECTORY_URL = (
    os.getenv("SEARCH_VECTORY_URL") or "http://localhost:8081/api/v1"
).strip()
MONGODB_URI = (os.getenv("MONGODB_URI") or "").strip()
MONGODB_DATABASE = (os.getenv("MONGODB_DATABASE") or "vectory").strip() or "vectory"

REDIS_HOST = (os.getenv("REDIS_HOST") or "").strip()
REDIS_PORT = (os.getenv("REDIS_PORT") or "").strip()
REDIS_PASSWORD = (os.getenv("REDIS_PASSWORD") or "").strip()


def is_redis_configured() -> bool:
    return bool(REDIS_HOST and REDIS_PORT and REDIS_PASSWORD)


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não está configurado")
