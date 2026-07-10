"""JSON-serializable dataclasses for retrieval evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GoldQuery:
    query_id: str
    query: str
    suite: str
    category: str
    language: str
    query_type: str
    relevance: dict[str, int]
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryEvaluation:
    query_id: str
    query: str
    retriever: str
    category: str
    language: str
    query_type: str
    retrieved_chunk_ids: list[str]
    retrieved_scores: list[float]
    gold_relevance: dict[str, int]
    metrics: dict[str, float]
    missed_gold_ids: list[str]
    first_relevant_rank: int | None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalEvaluationSummary:
    suite: str
    corpus_profile: str
    retriever: str
    query_count: int
    k_values: list[int]
    overall_metrics: dict[str, float]
    category_metrics: dict[str, dict[str, float]]
    language_metrics: dict[str, dict[str, float]]
    query_type_metrics: dict[str, dict[str, float]]
    query_results: list[QueryEvaluation]
    zero_hit_queries: list[str]
    worst_performing_queries: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegressionComparison:
    baseline_name: str
    current_metrics: dict[str, float]
    baseline_metrics: dict[str, float]
    deltas: dict[str, float]
    passed: bool
    failures: list[str]
    tolerance: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
