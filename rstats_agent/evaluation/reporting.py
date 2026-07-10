"""JSON and Markdown reports for retrieval evaluation summaries."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rstats_agent.evaluation.schemas import QueryEvaluation, RetrievalEvaluationSummary


LIMITATIONS = (
    "The query set is a small, project-maintained curated benchmark intended for regression testing.",
    "It does not represent the full R package ecosystem.",
    "Local-hash embeddings are deterministic test embeddings, not production semantic embeddings.",
    "The fixture-core and CRAN metadata corpora are deliberately small.",
    "This release evaluates retrieval only, not the correctness of generated R code.",
    "No statistical significance tests are performed.",
)


def _summary_list(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
) -> list[RetrievalEvaluationSummary]:
    if isinstance(summaries, RetrievalEvaluationSummary):
        return [summaries]
    values = list(summaries)
    if not values:
        raise ValueError("at least one evaluation summary is required")
    return values


def evaluation_report_payload(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
) -> dict[str, Any]:
    values = _summary_list(summaries)
    first = values[0]
    if any(
        summary.suite != first.suite
        or summary.corpus_profile != first.corpus_profile
        or summary.query_count != first.query_count
        or summary.k_values != first.k_values
        for summary in values[1:]
    ):
        raise ValueError("report summaries must share suite, corpus profile, query count, and k values")
    return {
        "report_type": "retrieval_evaluation",
        "suite": first.suite,
        "corpus_profile": first.corpus_profile,
        "query_count": first.query_count,
        "corpus_chunk_count": first.metadata.get("corpus_chunk_count"),
        "retrievers": [summary.retriever for summary in values],
        "k_values": first.k_values,
        "summaries": [summary.to_dict() for summary in values],
        "limitations": list(LIMITATIONS),
    }


def _metric_columns(k_values: list[int]) -> list[str]:
    max_k = max(k_values)
    return [
        *(f"recall@{k}" for k in k_values),
        f"hit_rate@{max_k}",
        f"mrr@{max_k}",
        f"ndcg@{max_k}",
    ]


def _metric_label(metric: str) -> str:
    prefix, k = metric.split("@", maxsplit=1)
    labels = {"recall": "Recall", "hit_rate": "HitRate", "mrr": "MRR", "ndcg": "nDCG"}
    return f"{labels[prefix]}@{k}"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]


def _overall_table(summaries: list[RetrievalEvaluationSummary]) -> list[str]:
    metrics = _metric_columns(summaries[0].k_values)
    rows = [
        [summary.retriever, *(f"{summary.overall_metrics[key]:.4f}" for key in metrics)]
        for summary in summaries
    ]
    return _table(["Retriever", *(_metric_label(key) for key in metrics)], rows)


def _group_table(
    summaries: list[RetrievalEvaluationSummary],
    attribute: str,
) -> list[str]:
    metrics = _metric_columns(summaries[0].k_values)
    rows: list[list[str]] = []
    for summary in summaries:
        grouped = getattr(summary, attribute)
        for group_name in sorted(grouped):
            rows.append(
                [group_name, summary.retriever, *(f"{grouped[group_name][key]:.4f}" for key in metrics)]
            )
    return _table(["Group", "Retriever", *(_metric_label(key) for key in metrics)], rows)


def _result_by_id(summary: RetrievalEvaluationSummary, query_id: str) -> QueryEvaluation:
    return next(result for result in summary.query_results if result.query_id == query_id)


def render_evaluation_markdown(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
) -> str:
    values = _summary_list(summaries)
    payload = evaluation_report_payload(values)
    max_k = max(values[0].k_values)
    lines = [
        "# Retrieval Evaluation Report",
        "",
        "## Evaluation Configuration",
        "",
        f"- Suite: `{payload['suite']}`",
        f"- Corpus profile: `{payload['corpus_profile']}`",
        f"- Query count: {payload['query_count']}",
        f"- Corpus chunk count: {payload['corpus_chunk_count']}",
        f"- Retrievers: {', '.join(f'`{name}`' for name in payload['retrievers'])}",
        f"- k values: {', '.join(str(k) for k in payload['k_values'])}",
        "- Embedding backend: `local-hash` for vector-enabled retrievers",
        "- Vector index backend: `numpy`",
        "",
        "## Overall Metrics",
        "",
        *_overall_table(values),
        "",
        "## Metrics by Category",
        "",
        *_group_table(values, "category_metrics"),
        "",
        "## Metrics by Language",
        "",
        *_group_table(values, "language_metrics"),
        "",
        "## Metrics by Query Type",
        "",
        *_group_table(values, "query_type_metrics"),
        "",
        "## Zero-hit Queries",
        "",
    ]
    zero_rows = 0
    for summary in values:
        for query_id in summary.zero_hit_queries:
            result = _result_by_id(summary, query_id)
            lines.append(
                f"- `{summary.retriever}` / `{query_id}`: {result.query} "
                f"(gold: {', '.join(sorted(result.gold_relevance))}; "
                f"retrieved: {', '.join(result.retrieved_chunk_ids)})"
            )
            zero_rows += 1
    if zero_rows == 0:
        lines.append("- None at the largest evaluated k.")
    lines.extend(["", "## Worst-performing Queries", ""])
    for summary in values:
        for query_id in summary.worst_performing_queries:
            result = _result_by_id(summary, query_id)
            lines.append(
                f"- `{summary.retriever}` / `{query_id}`: "
                f"Recall@{max_k}={result.metrics[f'recall@{max_k}']:.4f}, "
                f"MRR@{max_k}={result.metrics[f'reciprocal_rank@{max_k}']:.4f}, "
                f"nDCG@{max_k}={result.metrics[f'ndcg@{max_k}']:.4f}"
            )
    lines.extend(["", "## Retriever Comparison", ""])
    reference = values[0]
    for summary in values[1:]:
        differences = []
        for metric in _metric_columns(reference.k_values):
            delta = summary.overall_metrics[metric] - reference.overall_metrics[metric]
            differences.append(f"{_metric_label(metric)} {delta:+.4f}")
        lines.append(
            f"- `{summary.retriever}` minus `{reference.retriever}` observed macro averages: "
            + ", ".join(differences)
            + "."
        )
    if len(values) == 1:
        lines.append("- A single retriever was evaluated, so no cross-retriever delta is shown.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in LIMITATIONS)
    return "\n".join(lines) + "\n"


def write_evaluation_json(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(evaluation_report_payload(summaries), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_evaluation_markdown(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_evaluation_markdown(summaries), encoding="utf-8")
    return path
