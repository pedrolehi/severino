import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core.config import SEARCH_VECTORY_URL
from rag.config import RAG_ENABLE_RERANKING
from rag.ports import RetrievedChunk


class SearchVectoryAdapter:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or SEARCH_VECTORY_URL).rstrip("/")

    def search(
        self,
        *,
        query: str,
        collection_name: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        url = f"{self._base_url}/vector-search"
        payload = {
            "query": query,
            "collection_name": collection_name,
            "top_k": top_k,
            "enable_reranking": RAG_ENABLE_RERANKING,
        }
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(
                f"Erro na busca vetorial ({exc.code}): {detail}"
            ) from exc

        if not body.get("success"):
            raise ValueError(body.get("error") or "Busca vetorial falhou")

        chunks: list[RetrievedChunk] = []
        for item in body.get("results") or []:
            chunks.append(
                RetrievedChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    score=float(item.get("adjusted_score") or item.get("score") or 0),
                    metadata=dict(item.get("metadata") or {}),
                )
            )
        return chunks
