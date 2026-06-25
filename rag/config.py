import os

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_ENABLE_RERANKING = os.getenv("RAG_ENABLE_RERANKING", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}

VECTORY_ENV_BY_APP_ENV = {
    "dev": "dev",
    "hml": "homolog",
    "prod": "prod",
}

PROJECTS_COLLECTION = "projects"
