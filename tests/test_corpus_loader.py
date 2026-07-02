import json
from pathlib import Path
from uuid import uuid4

from rstats_agent.config import DEFAULT_CORPUS_PATH
from rstats_agent.knowledge.corpus_loader import identify_corpus_source, load_corpus, resolve_corpus_path


TEST_OUTPUT = Path(".test-output")


def _output_path(name: str) -> Path:
    TEST_OUTPUT.mkdir(exist_ok=True)
    return TEST_OUTPUT / f"{uuid4().hex}-{name}"


def test_loads_fixture_corpus_with_required_chunks():
    chunks = load_corpus(DEFAULT_CORPUS_PATH)

    assert len(chunks) >= 12
    chunk_ids = {chunk.chunk_id for chunk in chunks}
    assert "dplyr-filter" in chunk_ids
    assert "ggplot2-geom-point" in chunk_ids
    assert "lme4-sleepstudy-example" in chunk_ids
    assert all(chunk.priority in {"P0", "P1", "P2"} for chunk in chunks)
    assert all(chunk.license == "synthetic_fixture" for chunk in chunks)
    assert all(chunk.provenance == "handwritten_summary_for_offline_tests" for chunk in chunks)


def test_resolve_corpus_path_prefers_processed_when_present():
    processed = _output_path("loader-preferred-corpus.jsonl")
    fixture = _output_path("loader-preferred-fixture.jsonl")
    processed.write_text("", encoding="utf-8")
    fixture.write_text("", encoding="utf-8")

    assert resolve_corpus_path(processed_path=processed, fixture_path=fixture) == processed
    assert identify_corpus_source(processed, processed_path=processed, fixture_path=fixture) == "processed_corpus"


def test_resolve_corpus_path_falls_back_to_fixture_when_processed_missing():
    processed = _output_path("loader-missing-corpus.jsonl")
    fixture = _output_path("loader-fallback-fixture.jsonl")
    fixture.write_text("", encoding="utf-8")

    assert resolve_corpus_path(processed_path=processed, fixture_path=fixture) == fixture
    assert identify_corpus_source(fixture, processed_path=processed, fixture_path=fixture) == "fixture_fallback"


def test_load_corpus_prefers_processed_rows_when_present():
    processed = _output_path("loader-processed-corpus.jsonl")
    row = {
        "chunk_id": "renv-cran-package-overview",
        "source_type": "cran_package_overview",
        "package": "renv",
        "function": "__package__",
        "title": "renv CRAN package overview",
        "text": "Project-local R dependency management.",
        "source_url": "https://CRAN.R-project.org/package=renv",
        "license": "MIT + file LICENSE",
        "provenance": "cran_package_page",
        "priority": "P0",
        "package_version": "1.0.11",
        "published": "2025-01-16",
    }
    processed.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    chunks = load_corpus(processed_path=processed, fixture_path=DEFAULT_CORPUS_PATH)

    assert [chunk.chunk_id for chunk in chunks] == ["renv-cran-package-overview"]
    assert chunks[0].package_version == "1.0.11"
