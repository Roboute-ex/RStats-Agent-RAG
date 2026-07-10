import json
from pathlib import Path
from uuid import uuid4

from rstats_agent.evaluation.reporting import (
    render_evaluation_markdown,
    write_evaluation_json,
    write_evaluation_markdown,
)
from rstats_agent.evaluation.schemas import QueryEvaluation, RetrievalEvaluationSummary


TEST_OUTPUT = Path(".test-output")


def _output_dir(name: str) -> Path:
    path = TEST_OUTPUT / f"{uuid4().hex}-{name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _summary() -> RetrievalEvaluationSummary:
    result = QueryEvaluation(
        query_id="zero-query",
        query="find a missing chunk",
        retriever="tfidf",
        category="dplyr",
        language="en",
        query_type="debug",
        retrieved_chunk_ids=["other"],
        retrieved_scores=[0.1],
        gold_relevance={"gold": 3},
        metrics={
            "recall@1": 0.0,
            "hit_rate@1": 0.0,
            "reciprocal_rank@1": 0.0,
            "dcg@1": 0.0,
            "ndcg@1": 0.0,
        },
        missed_gold_ids=["gold"],
        first_relevant_rank=None,
    )
    metrics = {"recall@1": 0.0, "hit_rate@1": 0.0, "mrr@1": 0.0, "ndcg@1": 0.0}
    return RetrievalEvaluationSummary(
        suite="tiny",
        corpus_profile="fixture-core",
        retriever="tfidf",
        query_count=1,
        k_values=[1],
        overall_metrics=metrics,
        category_metrics={"dplyr": metrics},
        language_metrics={"en": metrics},
        query_type_metrics={"debug": metrics},
        query_results=[result],
        zero_hit_queries=["zero-query"],
        worst_performing_queries=["zero-query"],
        metadata={"corpus_chunk_count": 2},
    )


def test_json_report_is_serializable_and_written():
    path = write_evaluation_json(_summary(), _output_dir("reporting") / "report.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["report_type"] == "retrieval_evaluation"
    assert payload["summaries"][0]["query_results"][0]["query_id"] == "zero-query"


def test_markdown_contains_metric_zero_hit_and_limitations_sections():
    markdown = render_evaluation_markdown(_summary())
    assert "# Retrieval Evaluation Report" in markdown
    assert "| Retriever | Recall@1 | HitRate@1 | MRR@1 | nDCG@1 |" in markdown
    assert "## Zero-hit Queries" in markdown
    assert "zero-query" in markdown
    assert "## Limitations" in markdown
    assert "not production semantic embeddings" in markdown


def test_written_reports_do_not_embed_absolute_output_paths():
    output_dir = _output_dir("reporting-path") / "nested"
    json_path = write_evaluation_json(_summary(), output_dir / "report.json")
    markdown_path = write_evaluation_markdown(_summary(), output_dir / "report.md")
    absolute = str(output_dir.resolve())
    assert absolute not in json_path.read_text(encoding="utf-8")
    assert absolute not in markdown_path.read_text(encoding="utf-8")
