"""Dependency-free ranking metrics used by the retrieval benchmark."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def _validate_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")


def _validate_relevance(relevance: Mapping[str, int]) -> None:
    if not relevance:
        raise ValueError("gold relevance must not be empty")
    for chunk_id, grade in relevance.items():
        if not isinstance(chunk_id, str) or not chunk_id:
            raise ValueError("gold relevance chunk IDs must be non-empty strings")
        if isinstance(grade, bool) or not isinstance(grade, int) or grade < 0:
            raise ValueError("relevance grades must be non-negative integers")
    if not any(grade > 0 for grade in relevance.values()):
        raise ValueError("gold relevance must contain at least one positive grade")


def deduplicate_ranked_ids(ids: list[str]) -> list[str]:
    """Remove duplicate IDs while preserving their first ranked position."""

    seen: set[str] = set()
    unique: list[str] = []
    for chunk_id in ids:
        if chunk_id not in seen:
            seen.add(chunk_id)
            unique.append(chunk_id)
    return unique


def recall_at_k(ranked_ids: list[str], relevance: Mapping[str, int], k: int) -> float:
    _validate_k(k)
    _validate_relevance(relevance)
    relevant = {chunk_id for chunk_id, grade in relevance.items() if grade > 0}
    retrieved = set(deduplicate_ranked_ids(ranked_ids)[:k])
    return float(len(relevant.intersection(retrieved)) / len(relevant))


def hit_rate_at_k(ranked_ids: list[str], relevance: Mapping[str, int], k: int) -> float:
    _validate_k(k)
    _validate_relevance(relevance)
    relevant = {chunk_id for chunk_id, grade in relevance.items() if grade > 0}
    return float(any(chunk_id in relevant for chunk_id in deduplicate_ranked_ids(ranked_ids)[:k]))


def reciprocal_rank_at_k(ranked_ids: list[str], relevance: Mapping[str, int], k: int) -> float:
    _validate_k(k)
    _validate_relevance(relevance)
    relevant = {chunk_id for chunk_id, grade in relevance.items() if grade > 0}
    for rank, chunk_id in enumerate(deduplicate_ranked_ids(ranked_ids)[:k], start=1):
        if chunk_id in relevant:
            return float(1.0 / rank)
    return 0.0


def dcg_at_k(ranked_ids: list[str], relevance: Mapping[str, int], k: int) -> float:
    _validate_k(k)
    _validate_relevance(relevance)
    total = 0.0
    for rank, chunk_id in enumerate(deduplicate_ranked_ids(ranked_ids)[:k], start=1):
        grade = relevance.get(chunk_id, 0)
        total += (2**grade - 1) / math.log2(rank + 1)
    return float(total)


def ndcg_at_k(ranked_ids: list[str], relevance: Mapping[str, int], k: int) -> float:
    _validate_k(k)
    _validate_relevance(relevance)
    actual = dcg_at_k(ranked_ids, relevance, k)
    ideal_grades = sorted((grade for grade in relevance.values() if grade > 0), reverse=True)[:k]
    ideal = sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, start=1))
    if ideal <= 0.0:
        raise ValueError("ideal DCG must be positive")
    return float(actual / ideal)


def mean_reciprocal_rank(
    ranked_id_lists: Sequence[list[str]],
    relevances: Sequence[Mapping[str, int]],
    k: int,
) -> float:
    _validate_k(k)
    if not ranked_id_lists or len(ranked_id_lists) != len(relevances):
        raise ValueError("rankings and relevances must be non-empty and have equal length")
    values = [
        reciprocal_rank_at_k(ranked_ids, relevance, k)
        for ranked_ids, relevance in zip(ranked_id_lists, relevances, strict=True)
    ]
    return float(sum(values) / len(values))


def aggregate_query_metrics(query_metrics: Sequence[Mapping[str, float]]) -> dict[str, float]:
    """Macro-average metric dictionaries with identical keys."""

    if not query_metrics:
        raise ValueError("query metrics must not be empty")
    keys = set(query_metrics[0])
    if any(set(metrics) != keys for metrics in query_metrics[1:]):
        raise ValueError("query metric dictionaries must have identical keys")
    return {
        key: float(sum(float(metrics[key]) for metrics in query_metrics) / len(query_metrics))
        for key in sorted(keys)
    }
