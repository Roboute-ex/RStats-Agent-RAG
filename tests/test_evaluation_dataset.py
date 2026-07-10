import json
from pathlib import Path
from uuid import uuid4

import pytest

from rstats_agent.evaluation.dataset import (
    build_cran_metadata_evaluation_corpus,
    load_evaluation_suite,
    load_gold_queries,
    validate_gold_queries,
)
from rstats_agent.evaluation.schemas import GoldQuery


CORE_SUITE = Path("evaluation/suites/core_functions.jsonl")
CRAN_SUITE = Path("evaluation/suites/cran_metadata.jsonl")
TEST_OUTPUT = Path(".test-output")


def _output_path(name: str) -> Path:
    TEST_OUTPUT.mkdir(exist_ok=True)
    return TEST_OUTPUT / f"{uuid4().hex}-{name}"


def _record(**overrides):
    value = {
        "query_id": "q-1",
        "query": "find alpha",
        "suite": "test",
        "category": "pkg",
        "language": "en",
        "query_type": "function",
        "relevance": {"alpha": 3},
    }
    value.update(overrides)
    return value


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def test_load_gold_queries_accepts_valid_bilingual_jsonl():
    path = _write_jsonl(
        _output_path("evaluation-suite.jsonl"),
        [_record(), _record(query_id="q-2", query="查找 alpha", language="zh")],
    )
    queries = load_gold_queries(path)
    validate_gold_queries(queries, {"alpha"})
    assert [query.language for query in queries] == ["en", "zh"]


def test_load_gold_queries_rejects_invalid_json():
    path = _output_path("invalid-json-evaluation-suite.jsonl")
    path.write_text('{"query_id": "broken"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_gold_queries(path)


def test_validate_gold_queries_rejects_duplicate_query_id():
    queries = [GoldQuery(**_record()), GoldQuery(**_record(query="second"))]
    with pytest.raises(ValueError, match="duplicate query_id"):
        validate_gold_queries(queries, {"alpha"})


@pytest.mark.parametrize("missing_field", ["query", "relevance"])
def test_load_gold_queries_rejects_missing_required_fields(missing_field):
    record = _record()
    del record[missing_field]
    path = _write_jsonl(_output_path("invalid-evaluation-suite.jsonl"), [record])
    with pytest.raises(ValueError, match="missing fields"):
        load_gold_queries(path)


@pytest.mark.parametrize("grade", [-1, 1.5, True])
def test_validate_gold_queries_rejects_invalid_relevance_grade(grade):
    query = GoldQuery(**_record(relevance={"alpha": grade}))
    with pytest.raises(ValueError, match="invalid relevance grade"):
        validate_gold_queries([query], {"alpha"})


def test_validate_gold_queries_rejects_unknown_gold_chunk_id():
    query = GoldQuery(**_record(relevance={"unknown": 3}))
    with pytest.raises(ValueError, match="unknown gold chunk ID"):
        validate_gold_queries([query], {"alpha"})


@pytest.mark.parametrize("field_name", ["suite", "category", "language", "query_type"])
def test_validate_gold_queries_rejects_missing_dimensions(field_name):
    query = GoldQuery(**_record(**{field_name: ""}))
    with pytest.raises(ValueError, match=field_name):
        validate_gold_queries([query], {"alpha"})


@pytest.mark.parametrize("relevance", [{}, {"alpha": 0}])
def test_validate_gold_queries_rejects_empty_or_zero_relevance(relevance):
    query = GoldQuery(**_record(relevance=relevance))
    with pytest.raises(ValueError, match="relevance"):
        validate_gold_queries([query], {"alpha"})


def test_fixed_core_suite_has_required_queries_and_categories():
    queries, corpus = load_evaluation_suite(CORE_SUITE, "fixture-core")
    counts = {category: sum(query.category == category for query in queries) for category in {"dplyr", "ggplot2", "lme4"}}
    assert len(queries) == 30
    assert counts == {"dplyr": 10, "ggplot2": 10, "lme4": 10}
    for category in counts:
        category_queries = [query for query in queries if query.category == category]
        assert {query.language for query in category_queries} == {"en", "zh"}
        assert {query.query_type for query in category_queries} >= {"function", "concept", "debug"}
    assert len(corpus) == 14
    assert all("-cran-" not in chunk.chunk_id for chunk in corpus)


def test_cran_suite_is_built_from_offline_fixtures(monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network access is not allowed")

    monkeypatch.setattr("data.crawl_cran_packages.fetch_cran_package_page", fail_network)
    queries, corpus = load_evaluation_suite(CRAN_SUITE, "cran-metadata")
    counts = {package: sum(query.category == package for query in queries) for package in {"dplyr", "ggplot2", "lme4", "renv"}}
    assert len(queries) == 16
    assert counts == {"dplyr": 4, "ggplot2": 4, "lme4": 4, "renv": 4}
    assert {query.query_type for query in queries} == {"metadata"}
    assert {query.language for query in queries} == {"en", "zh"}
    assert len(corpus) == 16
    assert {query_id for query in queries for query_id in query.relevance}.issubset(
        {chunk.chunk_id for chunk in corpus}
    )


def test_cran_corpus_builder_is_deterministic():
    first = build_cran_metadata_evaluation_corpus()
    second = build_cran_metadata_evaluation_corpus()
    assert first == second
