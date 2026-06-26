from __future__ import annotations


def distance_to_similarity(distance_score: float) -> float:
    """Converte score de distância L2 do vectory (menor = melhor) para similaridade 0-1."""
    if distance_score <= 0:
        return 1.0
    if distance_score >= 1:
        return 0.0
    return max(0.0, 1.0 - distance_score)


def passes_similarity_threshold(distance_score: float, min_similarity: float) -> bool:
    return distance_to_similarity(distance_score) >= min_similarity
