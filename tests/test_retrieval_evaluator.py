from dataclasses import asdict

import pytest

from rstats_agent.evaluation.evaluator import (
    compare_retrievers,
    evaluate_query,
    retrieve_for_evaluation,
)
from rstats_agent.evaluation.schemas import GoldQuery
from rstats_agent.knowledge.hybrid_retriever import HybridRetriever
from rstats_agent.knowledge.vector_index import NumpyVectorIndex
from rstats_agent.schemas import KnowledgeChunk, RetrievalResult


def _chunk(chunk_id: str, package: str, text: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        source_type="test",
        package=package,
        function=chunk_id,
        title=chunk_id,
        text=text,
        source_url="https://example.test",
        license="synthetic_fixture",
        provenance="test",
        priority="P0",
    )


def _corpus() -> list[KnowledgeChunk]:
    return [
        _chunk("alpha", "pkg-a", "alpha filter rows and remove missing values"),
        _chunk("beta", "pkg-b", "beta scatter plot points and color mapping"),
        _chunk("gamma", "pkg-c", "gamma mixed model random effects"),
    ]


def _queries() -> list[GoldQuery]:
    return [
        GoldQuery("q-a", "alpha filter missing", "tiny", "clean", "en", "function", {"alpha": 3}),
        GoldQuery("q-b", "beta scatter plot", "tiny", "plot", "zh", "concept", {"beta": 3}),
        GoldQuery("q-c", "gamma random effects", "tiny", "model", "en", "debug", {"gamma": 3}),
    ]


def test_evaluate_query_exposes_ranked_scores_and_metrics():
    query = _queries()[0]
    chunk = _corpus()[0]
    retrieved = [RetrievalResult.from_chunk(chunk, 0.9)]
    result = evaluate_query(query, "tfidf", retrieved, [1, 3])
    assert result.retrieved_chunk_ids == ["alpha"]
    assert result.retrieved_scores == [pytest.approx(0.9)]
    assert result.metrics["recall@1"] == 1.0
    assert result.metrics["reciprocal_rank@3"] == 1.0
    assert result.first_relevant_rank == 1
    assert result.missed_gold_ids == []


def test_compare_retrievers_evaluates_tfidf_vector_and_hybrid():
    summaries = compare_retrievers(
        _queries(),
        _corpus(),
        retriever_names=["tfidf", "vector", "hybrid"],
        corpus_profile="tiny",
        k_values=[1, 3],
    )
    assert [summary.retriever for summary in summaries] == ["tfidf", "vector", "hybrid"]
    for summary in summaries:
        assert summary.query_count == 3
        assert len(summary.query_results) == 3
        assert set(summary.overall_metrics) >= {"recall@1", "hit_rate@3", "mrr@3", "ndcg@3"}
        assert set(summary.category_metrics) == {"clean", "model", "plot"}
        assert set(summary.language_metrics) == {"en", "zh"}
        assert set(summary.query_type_metrics) == {"concept", "debug", "function"}
        assert summary.metadata["corpus_chunk_count"] == 3
    assert summaries[1].metadata["embedding_backend"] == "local-hash"
    assert summaries[2].metadata["vector_index_backend"] == "numpy"


def test_evaluation_ranking_uses_chunk_id_as_tie_breaker():
    chunks = [
        _chunk("z-last", "same", "identical text"),
        _chunk("a-first", "same", "identical text"),
    ]
    results = retrieve_for_evaluation("unmatched-token", chunks, "tfidf", top_k=2)
    assert [result.chunk_id for result in results] == ["a-first", "z-last"]
    assert results[0].score == pytest.approx(results[1].score)


def test_numpy_vector_ties_use_chunk_id_order():
    chunks = [
        _chunk("z-last", "same", "same vector"),
        _chunk("a-first", "same", "same vector"),
    ]
    index = NumpyVectorIndex.build(chunks, [[1.0, 0.0], [1.0, 0.0]])
    results = index.search([1.0, 0.0], top_k=2)
    assert [result.chunk_id for result in results] == ["a-first", "z-last"]


def test_hybrid_ties_use_chunk_id_order():
    chunks = [
        _chunk("z-last", "same", "identical"),
        _chunk("a-first", "same", "identical"),
    ]

    class StubTfidf:
        knowledge_source = "test"

        def search(self, query, top_k):
            return [RetrievalResult.from_chunk(chunk, 1.0) for chunk in chunks]

        @staticmethod
        def _combine_query(query):
            return str(query)

    class StubEmbedding:
        def embed_query(self, query):
            return [1.0, 0.0]

    vector_index = NumpyVectorIndex.build(chunks, [[1.0, 0.0], [1.0, 0.0]])
    hybrid = HybridRetriever(
        tfidf_retriever=StubTfidf(),
        embedding_backend=StubEmbedding(),
        vector_index=vector_index,
        vector_weight=0.5,
        lexical_weight=0.5,
    )
    results = hybrid.search("tie", top_k=2)
    assert [result.chunk_id for result in results] == ["a-first", "z-last"]


def test_repeated_evaluation_is_identical():
    first = compare_retrievers(
        _queries(), _corpus(), ["tfidf", "vector", "hybrid"], "tiny", [1, 3]
    )
    second = compare_retrievers(
        _queries(), _corpus(), ["tfidf", "vector", "hybrid"], "tiny", [1, 3]
    )
    assert [asdict(summary) for summary in first] == [asdict(summary) for summary in second]


def test_retrieve_for_evaluation_rejects_unknown_retriever():
    with pytest.raises(ValueError, match="unsupported retriever"):
        retrieve_for_evaluation("alpha", _corpus(), "unknown")
