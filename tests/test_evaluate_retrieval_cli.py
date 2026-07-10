import json
from pathlib import Path
from uuid import uuid4

import requests

from scripts.evaluate_retrieval import main


CORE_SUITE = Path("evaluation/suites/core_functions.jsonl")
TEST_OUTPUT = Path(".test-output")


def _output_dir(name: str) -> Path:
    path = TEST_OUTPUT / f"{uuid4().hex}-{name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_core_suite_cli_succeeds_and_writes_reports_without_network(monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network access is not allowed")

    monkeypatch.setattr(requests, "get", fail_network)
    output_dir = _output_dir("evaluation-cli") / "results"
    code = main(
        [
            "--suite",
            str(CORE_SUITE),
            "--corpus-profile",
            "fixture-core",
            "--retrievers",
            "tfidf",
            "vector",
            "hybrid",
            "--k",
            "1",
            "3",
            "5",
            "--output-dir",
            str(output_dir),
            "--quiet",
        ]
    )
    assert code == 0
    assert (output_dir / "retrieval_evaluation.json").exists()
    assert (output_dir / "retrieval_evaluation.md").exists()
    payload = json.loads((output_dir / "retrieval_evaluation.json").read_text(encoding="utf-8"))
    assert payload["retrievers"] == ["tfidf", "vector", "hybrid"]
    assert payload["summaries"][1]["metadata"]["embedding_backend"] == "local-hash"
    assert payload["summaries"][1]["metadata"]["vector_index_backend"] == "numpy"


def test_invalid_suite_returns_exit_code_2_without_traceback(capsys):
    output_dir = _output_dir("invalid-evaluation-cli")
    code = main(
        [
            "--suite",
            str(output_dir / "missing.jsonl"),
            "--corpus-profile",
            "fixture-core",
            "--output-dir",
            str(output_dir / "results"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_baseline_regression_failure_returns_exit_code_3():
    output_dir = _output_dir("baseline-evaluation-cli")
    baseline_path = output_dir / "baseline.json"
    common = [
        "--suite",
        str(CORE_SUITE),
        "--corpus-profile",
        "fixture-core",
        "--retrievers",
        "tfidf",
        "--k",
        "1",
        "3",
        "5",
        "--quiet",
    ]
    write_code = main(
        [*common, "--output-dir", str(output_dir / "first"), "--write-baseline", str(baseline_path)]
    )
    assert write_code == 0
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    for metric in baseline["retrievers"]["tfidf"]["aggregate_metrics"]:
        baseline["retrievers"]["tfidf"]["aggregate_metrics"][metric] = 1.0
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    compare_code = main(
        [
            *common,
            "--output-dir",
            str(output_dir / "second"),
            "--compare-baseline",
            str(baseline_path),
            "--max-regression",
            "0.0",
        ]
    )
    assert compare_code == 3
