"""Serializable retrieval baselines and regression comparisons."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rstats_agent import __version__
from rstats_agent.evaluation.schemas import RegressionComparison, RetrievalEvaluationSummary


BASELINE_SCHEMA_VERSION = 1


def _summary_list(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
) -> list[RetrievalEvaluationSummary]:
    if isinstance(summaries, RetrievalEvaluationSummary):
        return [summaries]
    result = list(summaries)
    if not result:
        raise ValueError("at least one evaluation summary is required")
    return result


def _shared_value(summaries: list[RetrievalEvaluationSummary], field_name: str) -> Any:
    values = [getattr(summary, field_name) for summary in summaries]
    if any(value != values[0] for value in values[1:]):
        raise ValueError(f"baseline summaries must share the same {field_name}")
    return values[0]


def build_baseline_payload(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
    baseline_name: str = "retrieval-baseline",
) -> dict[str, Any]:
    values = _summary_list(summaries)
    corpus_counts = [summary.metadata.get("corpus_chunk_count") for summary in values]
    if any(count != corpus_counts[0] for count in corpus_counts[1:]):
        raise ValueError("baseline summaries must share the same corpus chunk count")
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "baseline_name": baseline_name,
        "project_version": __version__,
        "suite": _shared_value(values, "suite"),
        "corpus_profile": _shared_value(values, "corpus_profile"),
        "query_count": _shared_value(values, "query_count"),
        "corpus_chunk_count": corpus_counts[0],
        "k_values": _shared_value(values, "k_values"),
        "retrievers": {
            summary.retriever: {
                "retriever": summary.retriever,
                "aggregate_metrics": {
                    key: float(value) for key, value in sorted(summary.overall_metrics.items())
                },
            }
            for summary in values
        },
    }


def save_baseline(
    summaries: RetrievalEvaluationSummary | Sequence[RetrievalEvaluationSummary],
    path: Path,
    force: bool = False,
) -> dict[str, Any]:
    if path.exists() and not force:
        raise FileExistsError(f"baseline already exists; use --force to overwrite: {path}")
    payload = build_baseline_payload(summaries, baseline_name=path.stem)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def load_baseline(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to load baseline {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("baseline must be a JSON object")
    required = {
        "schema_version",
        "baseline_name",
        "project_version",
        "suite",
        "corpus_profile",
        "query_count",
        "corpus_chunk_count",
        "k_values",
        "retrievers",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"baseline is missing fields: {', '.join(sorted(missing))}")
    if payload["schema_version"] != BASELINE_SCHEMA_VERSION:
        raise ValueError(f"unsupported baseline schema version: {payload['schema_version']}")
    if not isinstance(payload["retrievers"], dict) or not payload["retrievers"]:
        raise ValueError("baseline retrievers must be a non-empty object")
    return payload


def _validate_compatible(current: RetrievalEvaluationSummary, baseline: dict[str, Any]) -> None:
    checks = {
        "suite": current.suite,
        "corpus_profile": current.corpus_profile,
        "query_count": current.query_count,
        "corpus_chunk_count": current.metadata.get("corpus_chunk_count"),
        "k_values": current.k_values,
    }
    for field_name, current_value in checks.items():
        if baseline.get(field_name) != current_value:
            raise ValueError(
                f"baseline {field_name} mismatch: baseline={baseline.get(field_name)!r}, "
                f"current={current_value!r}"
            )


def compare_against_baseline(
    current: RetrievalEvaluationSummary,
    baseline: dict[str, Any],
    tolerance: float,
) -> RegressionComparison:
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        raise ValueError("regression tolerance must be numeric")
    if not math.isfinite(float(tolerance)) or tolerance < 0:
        raise ValueError("regression tolerance must be a finite non-negative number")
    _validate_compatible(current, baseline)
    entry = baseline["retrievers"].get(current.retriever)
    if not isinstance(entry, dict):
        raise ValueError(f"baseline has no metrics for retriever: {current.retriever}")
    baseline_metrics = entry.get("aggregate_metrics")
    if not isinstance(baseline_metrics, dict):
        raise ValueError(f"baseline metrics are invalid for retriever: {current.retriever}")
    current_keys = set(current.overall_metrics)
    baseline_keys = set(baseline_metrics)
    if current_keys != baseline_keys:
        missing_current = sorted(baseline_keys.difference(current_keys))
        missing_baseline = sorted(current_keys.difference(baseline_keys))
        details: list[str] = []
        if missing_current:
            details.append(f"missing from current: {', '.join(missing_current)}")
        if missing_baseline:
            details.append(f"missing from baseline: {', '.join(missing_baseline)}")
        raise ValueError("metric set mismatch (" + "; ".join(details) + ")")
    deltas = {
        key: float(current.overall_metrics[key]) - float(baseline_metrics[key])
        for key in sorted(current_keys)
    }
    failures = [
        f"{key} declined by {-delta:.6f}, exceeding tolerance {float(tolerance):.6f}"
        for key, delta in deltas.items()
        if delta < -float(tolerance)
    ]
    return RegressionComparison(
        baseline_name=str(baseline["baseline_name"]),
        current_metrics={key: float(value) for key, value in sorted(current.overall_metrics.items())},
        baseline_metrics={key: float(value) for key, value in sorted(baseline_metrics.items())},
        deltas=deltas,
        passed=not failures,
        failures=failures,
        tolerance=float(tolerance),
    )


def assert_no_regression(comparison: RegressionComparison) -> None:
    if not comparison.passed:
        raise AssertionError("retrieval regression detected: " + "; ".join(comparison.failures))
