import os

from dotenv import load_dotenv

load_dotenv()

# LLM Provider configuration (ibm, internal, ou fallback)
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "ibm").strip().lower()

# IBM Watsonx
IBM_API_KEY = (
    os.getenv("IBM_IAM_APIKEY") or os.getenv("IBM_API_KEY") or ""
).strip() or None
IBM_PROJECT_ID = (os.getenv("IBM_PROJECT_ID") or "").strip() or None
IBM_BASE_URL = (
    os.getenv("IBM_BASE_URL") or "https://us-south.ml.cloud.ibm.com"
).strip().rstrip("/")
WATSONX_LLM_MODEL = (
    os.getenv("WATSONX_LLM_MODEL")
    or os.getenv("IBM_MODEL_ID")
    or "ibm/granite-4-h-small"
).strip()
IBM_API_VERSION = (os.getenv("IBM_API_VERSION") or "2024-07-23").strip()

# Internal LLM / JEV port (endpoint compatível ou gateway interno)
INTERNAL_LLM_BASE_URL = (
    os.getenv("INTERNAL_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or ""
).strip().rstrip("/")
INTERNAL_LLM_MODEL = (
    os.getenv("INTERNAL_LLM_MODEL") or os.getenv("OPENAI_MODEL_NAME") or "granite"
).strip()
INTERNAL_LLM_API_KEY = (
    os.getenv("INTERNAL_LLM_API_KEY") or "internal"
).strip()
INTERNAL_LLM_TIMEOUT_S = float(os.getenv("INTERNAL_LLM_TIMEOUT_S") or "3.0")
INTERNAL_LLM_CONNECT_TIMEOUT_S = float(
    os.getenv("INTERNAL_LLM_CONNECT_TIMEOUT_S") or "1.2"
)

# Chave legada/opcional da OpenAI (não mais obrigatória)
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip() or None

APP_ENV = (os.getenv("APP_ENV") or "dev").strip().lower()
SEARCH_VECTORY_URL = (
    os.getenv("SEARCH_VECTORY_URL") or "http://localhost:8081/api/v1"
).strip()
# S2S com search-vectory (header X-Internal-Token). Mesmo valor de INTERNAL_API_TOKEN.
SEARCH_VECTORY_INTERNAL_TOKEN = (
    os.getenv("SEARCH_VECTORY_INTERNAL_TOKEN") or os.getenv("INTERNAL_API_TOKEN") or ""
).strip() or None
# Flag para controlar se tenta /rag/answer/stream antes do fallback síncrono.
# Default False enquanto o pod do search-vectory não tiver /stream liberado nos internal_paths.
SEARCH_VECTORY_STREAM_ENABLED = os.getenv("SEARCH_VECTORY_STREAM_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
MONGODB_URI = (os.getenv("MONGODB_URI") or "").strip()
MONGODB_DATABASE = (os.getenv("MONGODB_DATABASE") or "vectory").strip() or "vectory"

REDIS_HOST = (os.getenv("REDIS_HOST") or "").strip()
REDIS_PORT = (os.getenv("REDIS_PORT") or "").strip()
REDIS_PASSWORD = (os.getenv("REDIS_PASSWORD") or "").strip()

# OpenJEV (router e demais decisões tipadas)
OPENJEV_BASE_URL = (
    (os.getenv("OPENJEV_BASE_URL") or "http://10.1.0.110:8011").strip().rstrip("/")
)
OPENJEV_API_KEY = (os.getenv("OPENJEV_API_KEY") or "").strip() or None
OPENJEV_MODEL = (os.getenv("OPENJEV_MODEL") or "jev-latest").strip() or "jev-latest"
OPENJEV_TIMEOUT_S = float(os.getenv("OPENJEV_TIMEOUT_S") or "2.0")
OPENJEV_CONNECT_TIMEOUT_S = float(os.getenv("OPENJEV_CONNECT_TIMEOUT_S") or "1.0")
USE_JEV_ROUTER = (os.getenv("USE_JEV_ROUTER") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
}


def is_redis_configured() -> bool:
    return bool(REDIS_HOST and REDIS_PORT and REDIS_PASSWORD)

