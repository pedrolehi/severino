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
            raw_distance = float(
                item.get("distance")
                if item.get("distance") is not None
                else item.get("score")
                if item.get("score") is not None
                else 1.0
            )
            adjusted_raw = item.get("adjusted_score")
            adjusted_score = (
                float(adjusted_raw) if adjusted_raw is not None else None
            )
            chunks.append(
                RetrievedChunk(
                    id=str(item.get("id", "")),
                    content=str(item.get("content", "")),
                    score=raw_distance,
                    metadata=dict(item.get("metadata") or {}),
                    similarity=distance_to_similarity(raw_distance),
                    adjusted_score=adjusted_score,
                )
            )
        return chunks
