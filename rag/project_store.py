from typing import Literal, cast

from core.database.mongo.client import get_meta_collection, is_mongo_configured
from rag.config import PROJECTS_COLLECTION, VECTORY_ENV_BY_APP_ENV

VectoryEnvironment = Literal["dev", "homolog", "prod"]
AppEnvironment = Literal["dev", "hml", "prod"]


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
    project = fetch_project_doc(project_id)
    vectory_env = resolve_vectory_environment(app_env)
    collections = project.get("collections") or {}
    collection_name = collections.get(vectory_env)
    if not collection_name:
        raise ProjectStoreError(
            f"Collection não configurada para projeto '{project_id}' "
            f"no ambiente '{vectory_env}'"
        )
    return str(collection_name)
