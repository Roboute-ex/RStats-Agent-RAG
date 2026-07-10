"""Deterministic adapters and runners for retrieval evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from rstats_agent import __version__
from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.evaluation.metrics import (
    aggregate_query_metrics,
    dcg_at_k,
    hit_rate_at_k,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)
from rstats_agent.evaluation.schemas import GoldQuery, QueryEvaluation, RetrievalEvaluationSummary
from rstats_agent.knowledge.hybrid_retriever import HybridRetriever
from rstats_agent.knowledge.retriever import LocalTfidfRetriever
from rstats_agent.knowledge.vector_index import NumpyVectorIndex
from rstats_agent.schemas import KnowledgeChunk, RetrievalResult


SUPPORTED_RETRIEVERS = {"tfidf", "vector", "hybrid"}
DEFAULT_K_VALUES = (1, 3, 5)


class _Searchable(Protocol):
    def search(self, query: str | dict[str, str], top_k: int) -> list[RetrievalResult]: ...


@dataclass
class _LocalVectorRetriever:
    embedding_backend: LocalHashEmbeddingBackend
    vector_index: NumpyVectorIndex

    def search(self, query: str | dict[str, str], top_k: int) -> list[RetrievalResult]:
        query_text = LocalTfidfRetriever._combine_query(query)
        embedding = self.embedding_backend.embed_query(query_text)
        return self.vector_index.search(embedding, top_k=top_k)


def _normalize_k_values(k_values: Sequence[int]) -> list[int]:
    if not k_values:
        raise ValueError("k values must not be empty")
    if any(isinstance(k, bool) or not isinstance(k, int) or k <= 0 for k in k_values):
        raise ValueError("all k values must be positive integers")
    return sorted(set(k_values))


def _build_vector_parts(
    corpus: list[KnowledgeChunk],
) -> tuple[LocalHashEmbeddingBackend, NumpyVectorIndex]:
    backend = LocalHashEmbeddingBackend()
    documents = [LocalTfidfRetriever._document_text(chunk) for chunk in corpus]
    index = NumpyVectorIndex.build(corpus, backend.embed_texts(documents))
    return backend, index


def _build_retriever(
    corpus: list[KnowledgeChunk],
    retriever_name: str,
    hybrid_vector_weight: float,
    hybrid_lexical_weight: float,
) -> _Searchable:
    if retriever_name not in SUPPORTED_RETRIEVERS:
        supported = ", ".join(sorted(SUPPORTED_RETRIEVERS))
        raise ValueError(f"unsupported retriever {retriever_name!r}; choose one of: {supported}")
    tfidf = LocalTfidfRetriever(chunks=corpus, knowledge_source="evaluation_fixture")
    if retriever_name == "tfidf":
        return tfidf
    backend, index = _build_vector_parts(corpus)
    if retriever_name == "vector":
        return _LocalVectorRetriever(backend, index)
    return HybridRetriever(
        tfidf_retriever=tfidf,
        embedding_backend=backend,
        vector_index=index,
        vector_weight=hybrid_vector_weight,
        lexical_weight=hybrid_lexical_weight,
    )


def _stable_results(results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
    by_id: dict[str, RetrievalResult] = {}
    for result in results:
        by_id.setdefault(result.chunk_id, result)
    return sorted(by_id.values(), key=lambda result: (-result.score, result.chunk_id))[:top_k]


def _retrieve_with(
    retriever: _Searchable,
    query: str,
    corpus_size: int,
    top_k: int,
) -> list[RetrievalResult]:
    return _stable_results(retriever.search(query, top_k=corpus_size), top_k=top_k)


def retrieve_for_evaluation(
    query: str,
    corpus: list[KnowledgeChunk],
    retriever_name: str,
    top_k: int = 5,
    hybrid_vector_weight: float = 0.6,
    hybrid_lexical_weight: float = 0.4,
) -> list[RetrievalResult]:
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    retriever = _build_retriever(
        corpus,
        retriever_name,
        hybrid_vector_weight,
        hybrid_lexical_weight,
    )
    return _retrieve_with(retriever, query, len(corpus), top_k)


def evaluate_query(
    gold_query: GoldQuery,
    retriever_name: str,
    retrieved: list[RetrievalResult],
    k_values: Sequence[int] = DEFAULT_K_VALUES,
) -> QueryEvaluation:
    normalized_k = _normalize_k_values(k_values)
    ranked_ids = [result.chunk_id for result in retrieved]
    metrics: dict[str, float] = {}
    for k in normalized_k:
        metrics[f"recall@{k}"] = recall_at_k(ranked_ids, gold_query.relevance, k)
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(ranked_ids, gold_query.relevance, k)
        metrics[f"reciprocal_rank@{k}"] = reciprocal_rank_at_k(ranked_ids, gold_query.relevance, k)
        metrics[f"dcg@{k}"] = dcg_at_k(ranked_ids, gold_query.relevance, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(ranked_ids, gold_query.relevance, k)
    relevant_ids = {chunk_id for chunk_id, grade in gold_query.relevance.items() if grade > 0}
    first_rank = next(
        (rank for rank, chunk_id in enumerate(ranked_ids, start=1) if chunk_id in relevant_ids),
        None,
    )
    return QueryEvaluation(
        query_id=gold_query.query_id,
        query=gold_query.query,
        retriever=retriever_name,
        category=gold_query.category,
        language=gold_query.language,
        query_type=gold_query.query_type,
        retrieved_chunk_ids=ranked_ids,
        retrieved_scores=[float(result.score) for result in retrieved],
        gold_relevance=dict(gold_query.relevance),
        metrics=metrics,
        missed_gold_ids=sorted(relevant_ids.difference(ranked_ids)),
        first_relevant_rank=first_rank,
        diagnostics={"notes": gold_query.notes} if gold_query.notes else {},
    )


def _macro_metrics(results: Sequence[QueryEvaluation]) -> dict[str, float]:
    if not results:
        raise ValueError("cannot aggregate an empty query result list")
    per_query: list[dict[str, float]] = []
    for result in results:
        mapped: dict[str, float] = {}
        for key, value in result.metrics.items():
            if key.startswith("reciprocal_rank@"):
                key = key.replace("reciprocal_rank@", "mrr@", 1)
            if not key.startswith("dcg@"):
                mapped[key] = value
        per_query.append(mapped)
    return aggregate_query_metrics(per_query)


def _group_metrics(
    results: Sequence[QueryEvaluation],
    field_name: str,
) -> dict[str, dict[str, float]]:
    groups: dict[str, list[QueryEvaluation]] = defaultdict(list)
    for result in results:
        groups[str(getattr(result, field_name))].append(result)
    return {name: _macro_metrics(groups[name]) for name in sorted(groups)}


def evaluate_retriever(
    gold_queries: list[GoldQuery],
    corpus: list[KnowledgeChunk],
    retriever_name: str,
    corpus_profile: str,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
    hybrid_vector_weight: float = 0.6,
    hybrid_lexical_weight: float = 0.4,
) -> RetrievalEvaluationSummary:
    if not gold_queries:
        raise ValueError("gold queries must not be empty")
    if not corpus:
        raise ValueError("corpus must not be empty")
    normalized_k = _normalize_k_values(k_values)
    retriever = _build_retriever(
        corpus,
        retriever_name,
        hybrid_vector_weight,
        hybrid_lexical_weight,
    )
    top_k = max(normalized_k)
    query_results = [
        evaluate_query(
            gold_query,
            retriever_name,
            _retrieve_with(retriever, gold_query.query, len(corpus), top_k),
            normalized_k,
        )
        for gold_query in gold_queries
    ]
    zero_hit = [
        result.query_id
        for result in query_results
        if result.metrics[f"hit_rate@{top_k}"] == 0.0
    ]
    worst = sorted(
        query_results,
        key=lambda result: (
            result.metrics[f"recall@{top_k}"],
            result.metrics[f"reciprocal_rank@{top_k}"],
            result.metrics[f"ndcg@{top_k}"],
            result.query_id,
        ),
    )[: min(5, len(query_results))]
    uses_vector = retriever_name in {"vector", "hybrid"}
    return RetrievalEvaluationSummary(
        suite=gold_queries[0].suite,
        corpus_profile=corpus_profile,
        retriever=retriever_name,
        query_count=len(gold_queries),
        k_values=normalized_k,
        overall_metrics=_macro_metrics(query_results),
        category_metrics=_group_metrics(query_results, "category"),
        language_metrics=_group_metrics(query_results, "language"),
        query_type_metrics=_group_metrics(query_results, "query_type"),
        query_results=query_results,
        zero_hit_queries=zero_hit,
        worst_performing_queries=[result.query_id for result in worst],
        metadata={
            "project_version": __version__,
            "corpus_chunk_count": len(corpus),
            "embedding_backend": "local-hash" if uses_vector else "not-applicable",
            "vector_index_backend": "numpy" if uses_vector else "not-applicable",
            "hybrid_vector_weight": hybrid_vector_weight if retriever_name == "hybrid" else None,
            "hybrid_lexical_weight": hybrid_lexical_weight if retriever_name == "hybrid" else None,
        },
    )


def evaluate_suite(
    gold_queries: list[GoldQuery],
    corpus: list[KnowledgeChunk],
    retriever_name: str,
    corpus_profile: str,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
    hybrid_vector_weight: float = 0.6,
    hybrid_lexical_weight: float = 0.4,
) -> RetrievalEvaluationSummary:
    return evaluate_retriever(
        gold_queries,
        corpus,
        retriever_name,
        corpus_profile,
        k_values,
        hybrid_vector_weight,
        hybrid_lexical_weight,
    )


def evaluate_tfidf(
    gold_queries: list[GoldQuery],
    corpus: list[KnowledgeChunk],
    corpus_profile: str,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
) -> RetrievalEvaluationSummary:
    return evaluate_retriever(gold_queries, corpus, "tfidf", corpus_profile, k_values)


def evaluate_vector(
    gold_queries: list[GoldQuery],
    corpus: list[KnowledgeChunk],
    corpus_profile: str,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
) -> RetrievalEvaluationSummary:
    return evaluate_retriever(gold_queries, corpus, "vector", corpus_profile, k_values)


def evaluate_hybrid(
    gold_queries: list[GoldQuery],
    corpus: list[KnowledgeChunk],
    corpus_profile: str,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
    vector_weight: float = 0.6,
    lexical_weight: float = 0.4,
) -> RetrievalEvaluationSummary:
    return evaluate_retriever(
        gold_queries,
        corpus,
        "hybrid",
        corpus_profile,
        k_values,
        vector_weight,
        lexical_weight,
    )


def compare_retrievers(
    gold_queries: list[GoldQuery],
    corpus: list[KnowledgeChunk],
    retriever_names: Sequence[str] = ("tfidf", "vector", "hybrid"),
    corpus_profile: str = "fixture-core",
    k_values: Sequence[int] = DEFAULT_K_VALUES,
    hybrid_vector_weight: float = 0.6,
    hybrid_lexical_weight: float = 0.4,
) -> list[RetrievalEvaluationSummary]:
    if not retriever_names:
        raise ValueError("retriever names must not be empty")
    return [
        evaluate_retriever(
            gold_queries,
            corpus,
            name,
            corpus_profile,
            k_values,
            hybrid_vector_weight,
            hybrid_lexical_weight,
        )
        for name in retriever_names
    ]
