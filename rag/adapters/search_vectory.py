from __future__ import annotations

from rag.http_client import VectoryHttpError, post_json
from rag.policy import SearchPolicy
from rag.ports import RetrievedChunk
from rag.scoring import distance_to_similarity


class SearchVectoryAdapter:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def search(
        self,
        *,
        query: str,
        collection_name: str,
        search_policy: SearchPolicy,
    ) -> list[RetrievedChunk]:
        payload = {
            "query": query,
            "collection_name": collection_name,
            "top_k": search_policy.top_k,
            "search_buffer": search_policy.search_buffer,
            "enable_reranking": search_policy.enable_reranking,
            "reranker_mode": search_policy.reranker_mode,
            "use_hybrid_search": search_policy.use_hybrid_search,
            "enable_query_expansion": search_policy.enable_query_expansion,
            "return_full_metadata": True,
        }

        try:
            body = post_json(
                "vector-search",
                payload,
                base_url=self._base_url,
            )
        except VectoryHttpError as exc:
            raise ValueError(exc.detail) from exc

        if not body.get("success"):
            raise ValueError(body.get("error") or "Busca vetorial falhou")

        chunks: list[RetrievedChunk] = []
        for item in body.get("results") or []:
            distance_score = float(
                item.get("adjusted_score")
                if item.get("adjusted_score") is not None
                else item.get("score")
                or 0
            )
            chunks.append(
                RetrievedChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    score=distance_score,
                    metadata=dict(item.get("metadata") or {}),
                    similarity=distance_to_similarity(distance_score),
                )
            )
        return chunks
