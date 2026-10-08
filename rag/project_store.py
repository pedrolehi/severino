from typing import Literal, cast

from core.database.mongo.client import get_meta_collection, is_mongo_configured
from rag.config import PROJECTS_COLLECTION, VECTORY_ENV_BY_APP_ENV

VectoryEnvironment = Literal["dev", "homolog", "prod"]
AppEnvironment = Literal["dev", "hml", "prod"]

# Mapeamento para ambientes onde a collection Milvus tem nome específico.
# Em homologação, o Search-Vectory / Milvus armazena os dados da Intranet na collection 'intranet_dev'
# (mesmo mapeamento que o Watson Orchestrate utiliza com sucesso).
COLLECTION_OVERRIDES_BY_ENV: dict[str, dict[str, str]] = {
    "homolog": {
        "intranet": "intranet_dev",
        "intranet_homolog": "intranet_dev",
    },
    "hml": {
        "intranet": "intranet_dev",
        "intranet_homolog": "intranet_dev",
    },
}


class ProjectStoreError(Exception):
    pass


def resolve_vectory_environment(app_env: str) -> VectoryEnvironment:
    env = cast(AppEnvironment, app_env.strip().lower())
    if env not in VECTORY_ENV_BY_APP_ENV:
        raise ProjectStoreError(f"APP_ENV inválido: {env}")
    return cast(VectoryEnvironment, VECTORY_ENV_BY_APP_ENV[env])


def fetch_project_doc(project_id: str) -> dict:
    if not is_mongo_configured():
        raise ProjectStoreError("MONGODB_URI não configurado")

    coll = get_meta_collection(PROJECTS_COLLECTION)
    if coll is None:
        raise ProjectStoreError("MongoDB indisponível")

    doc = coll.find_one({"_id": project_id})
    if not doc:
        doc = coll.find_one({"slug": project_id})
    if not doc:
        raise ProjectStoreError(f"Projeto '{project_id}' não encontrado no Mongo")
    return doc


def resolve_collection_name(project_id: str, app_env: str) -> str:
    env_clean = (app_env or "").strip().lower()
    override = COLLECTION_OVERRIDES_BY_ENV.get(env_clean, {}).get(project_id)
    if override:
        return override

    project = fetch_project_doc(project_id)
    vectory_env = resolve_vectory_environment(app_env)
    collections = project.get("collections") or {}
    collection_name = collections.get(vectory_env)
    if not collection_name:
        raise ProjectStoreError(
            f"Collection não configurada para projeto '{project_id}' "
            f"no ambiente '{vectory_env}' (app_env={app_env})"
        )
    resolved = str(collection_name)
    return COLLECTION_OVERRIDES_BY_ENV.get(env_clean, {}).get(resolved, resolved)


def resolve_assistant_collection(
    *,
    project_id: str,
    app_env: str,
    collection_name: str | None = None,
) -> str:
    """Override explícito ou lookup Mongo projects[env], com alinhamento de homolog."""
    override = (collection_name or "").strip()
    if override:
        env_clean = (app_env or "").strip().lower()
        return COLLECTION_OVERRIDES_BY_ENV.get(env_clean, {}).get(override, override)
    return resolve_collection_name(project_id, app_env)

