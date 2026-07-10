import json
from pathlib import Path
from uuid import uuid4

import pytest

from rstats_agent.evaluation.regression import (
    assert_no_regression,
    compare_against_baseline,
    load_baseline,
    save_baseline,
)
from rstats_agent.evaluation.schemas import RetrievalEvaluationSummary


TEST_OUTPUT = Path(".test-output")


def _output_path(name: str) -> Path:
    TEST_OUTPUT.mkdir(exist_ok=True)
    return TEST_OUTPUT / f"{uuid4().hex}-{name}"


def _summary(
    *,
    recall: float = 0.8,
    mrr: float = 0.9,
    query_count: int = 10,
    corpus_count: int = 14,
) -> RetrievalEvaluationSummary:
    return RetrievalEvaluationSummary(
        suite="core_functions",
        corpus_profile="fixture-core",
        retriever="tfidf",
        query_count=query_count,
        k_values=[1, 3, 5],
        overall_metrics={"recall@5": recall, "mrr@5": mrr},
        category_metrics={},
        language_metrics={},
        query_type_metrics={},
        query_results=[],
        zero_hit_queries=[],
        worst_performing_queries=[],
        metadata={"corpus_chunk_count": corpus_count},
    )


def test_save_and_load_baseline_round_trip():
    path = _output_path("baseline.json")
    saved = save_baseline(_summary(), path)
    loaded = load_baseline(path)
    assert loaded == saved
    assert loaded["project_version"] == "0.6.0"
    assert loaded["retrievers"]["tfidf"]["aggregate_metrics"]["recall@5"] == 0.8
    serialized = path.read_text(encoding="utf-8")
    assert str(Path.cwd().resolve()) not in serialized
    assert "timestamp" not in serialized


def test_equal_result_passes_baseline_comparison():
    path = _output_path("baseline.json")
    baseline = save_baseline(_summary(), path)
    comparison = compare_against_baseline(_summary(), baseline, tolerance=0.0)
    assert comparison.passed
    assert all(delta == pytest.approx(0.0) for delta in comparison.deltas.values())
    assert_no_regression(comparison)


def test_small_tolerated_decline_passes():
    baseline = save_baseline(_summary(), _output_path("baseline.json"))
    comparison = compare_against_baseline(_summary(recall=0.79), baseline, tolerance=0.02)
    assert comparison.passed


def test_excessive_decline_fails():
    baseline = save_baseline(_summary(), _output_path("baseline.json"))
    comparison = compare_against_baseline(_summary(recall=0.7), baseline, tolerance=0.02)
    assert not comparison.passed
    assert comparison.failures
    with pytest.raises(AssertionError, match="regression"):
        assert_no_regression(comparison)


@pytest.mark.parametrize(
    ("current", "message"),
    [(_summary(query_count=11), "query_count mismatch"), (_summary(corpus_count=15), "corpus_chunk_count mismatch")],
)
def test_structural_mismatch_rejects_comparison(current, message):
    baseline = save_baseline(_summary(), _output_path("baseline.json"))
    with pytest.raises(ValueError, match=message):
        compare_against_baseline(current, baseline, tolerance=0.0)


def test_missing_metric_rejects_comparison():
    path = _output_path("baseline.json")
    baseline = save_baseline(_summary(), path)
    del baseline["retrievers"]["tfidf"]["aggregate_metrics"]["mrr@5"]
    with pytest.raises(ValueError, match="metric set mismatch"):
        compare_against_baseline(_summary(), baseline, tolerance=0.0)


def test_overwrite_requires_force():
    path = _output_path("baseline.json")
    save_baseline(_summary(), path)
    with pytest.raises(FileExistsError, match="--force"):
        save_baseline(_summary(recall=0.9), path)
    save_baseline(_summary(recall=0.9), path, force=True)
    assert json.loads(path.read_text(encoding="utf-8"))["retrievers"]["tfidf"]["aggregate_metrics"]["recall@5"] == 0.9
