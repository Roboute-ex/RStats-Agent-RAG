import math

import pytest

from rstats_agent.evaluation.metrics import (
    aggregate_query_metrics,
    dcg_at_k,
    deduplicate_ranked_ids,
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)


GOLD = {"a": 3, "b": 2, "c": 1}


def test_deduplicate_ranked_ids_preserves_first_position():
    assert deduplicate_ranked_ids(["a", "x", "a", "b", "x"]) == ["a", "x", "b"]


def test_recall_at_k_uses_positive_gold_and_deduplicated_ranks():
    assert recall_at_k(["a", "a", "x", "b"], GOLD, 3) == pytest.approx(2 / 3)


def test_hit_rate_at_k_is_binary():
    assert hit_rate_at_k(["x", "b"], GOLD, 1) == 0.0
    assert hit_rate_at_k(["x", "b"], GOLD, 2) == 1.0


def test_reciprocal_rank_at_k_uses_first_relevant_rank():
    assert reciprocal_rank_at_k(["x", "b", "a"], GOLD, 3) == pytest.approx(0.5)
    assert reciprocal_rank_at_k(["x", "y", "a"], GOLD, 2) == 0.0


def test_mean_reciprocal_rank_is_macro_average():
    rankings = [["a"], ["x", "b"], ["x"]]
    relevances = [{"a": 1}, {"b": 1}, {"c": 1}]
    assert mean_reciprocal_rank(rankings, relevances, 2) == pytest.approx(0.5)


def test_dcg_at_k_uses_graded_exponential_gain():
    expected = 7.0 + 3.0 / math.log2(3)
    assert dcg_at_k(["a", "b"], GOLD, 2) == pytest.approx(expected)


def test_ndcg_at_k_compares_with_ideal_graded_order():
    ideal = ndcg_at_k(["a", "b", "c"], GOLD, 3)
    reversed_score = ndcg_at_k(["c", "b", "a"], GOLD, 3)
    assert ideal == pytest.approx(1.0)
    assert 0.0 < reversed_score < 1.0


def test_metrics_return_zero_when_no_relevant_chunk_is_retrieved():
    assert recall_at_k(["x", "y"], GOLD, 2) == 0.0
    assert hit_rate_at_k(["x", "y"], GOLD, 2) == 0.0
    assert reciprocal_rank_at_k(["x", "y"], GOLD, 2) == 0.0
    assert dcg_at_k(["x", "y"], GOLD, 2) == 0.0
    assert ndcg_at_k(["x", "y"], GOLD, 2) == 0.0


@pytest.mark.parametrize(
    "metric",
    [recall_at_k, hit_rate_at_k, reciprocal_rank_at_k, dcg_at_k, ndcg_at_k],
)
@pytest.mark.parametrize("k", [0, -1, True])
def test_metrics_reject_invalid_k(metric, k):
    with pytest.raises(ValueError, match="positive integer"):
        metric(["a"], GOLD, k)


@pytest.mark.parametrize(
    "relevance",
    [{}, {"a": 0}, {"a": -1}, {"a": 1.5}, {"a": True}],
)
def test_metrics_reject_invalid_or_empty_relevance(relevance):
    with pytest.raises(ValueError, match="relevance"):
        recall_at_k(["a"], relevance, 1)


def test_aggregate_query_metrics_macro_averages_each_key():
    aggregate = aggregate_query_metrics(
        [{"recall@1": 1.0, "mrr@1": 1.0}, {"recall@1": 0.0, "mrr@1": 0.5}]
    )
    assert aggregate == {"mrr@1": pytest.approx(0.75), "recall@1": pytest.approx(0.5)}
