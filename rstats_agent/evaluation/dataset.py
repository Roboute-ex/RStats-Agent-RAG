"""Gold query loading and fixed offline corpus profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data.build_corpus import build_corpus_from_packages
from data.crawl_cran_packages import DEFAULT_FIXTURE_DIR, DEFAULT_PACKAGES, crawl_packages
from rstats_agent.config import DEFAULT_CORPUS_PATH
from rstats_agent.evaluation.schemas import GoldQuery
from rstats_agent.knowledge.corpus_loader import load_corpus
from rstats_agent.schemas import KnowledgeChunk


SUPPORTED_LANGUAGES = {"zh", "en"}
SUPPORTED_QUERY_TYPES = {"function", "concept", "debug", "metadata"}
SUPPORTED_CORPUS_PROFILES = {"fixture-core", "cran-metadata"}
REQUIRED_QUERY_FIELDS = {
    "query_id",
    "query",
    "suite",
    "category",
    "language",
    "query_type",
    "relevance",
}


def _gold_query_from_record(record: dict[str, Any], line_number: int) -> GoldQuery:
    missing = REQUIRED_QUERY_FIELDS.difference(record)
    if missing:
        raise ValueError(f"Gold query line {line_number} is missing fields: {', '.join(sorted(missing))}")
    relevance = record["relevance"]
    if not isinstance(relevance, dict):
        raise ValueError(f"Gold query line {line_number} relevance must be an object")
    return GoldQuery(
        query_id=record["query_id"],
        query=record["query"],
        suite=record["suite"],
        category=record["category"],
        language=record["language"],
        query_type=record["query_type"],
        relevance=dict(relevance),
        notes=record.get("notes"),
    )


def load_gold_queries(path: Path) -> list[GoldQuery]:
    queries: list[GoldQuery] = []
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Unable to read evaluation suite {path}: {exc}") from exc
    with handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on gold query line {line_number}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Gold query line {line_number} must be a JSON object")
            queries.append(_gold_query_from_record(record, line_number))
    if not queries:
        raise ValueError(f"Evaluation suite is empty: {path}")
    return queries


def validate_gold_queries(queries: list[GoldQuery], corpus_chunk_ids: set[str]) -> None:
    if not queries:
        raise ValueError("evaluation suite must contain at least one query")
    seen: set[str] = set()
    suites: set[str] = set()
    for query in queries:
        if not isinstance(query.query_id, str) or not query.query_id.strip():
            raise ValueError("query_id must be a non-empty string")
        if query.query_id in seen:
            raise ValueError(f"duplicate query_id: {query.query_id}")
        seen.add(query.query_id)
        if not isinstance(query.query, str) or not query.query.strip():
            raise ValueError(f"query must not be empty: {query.query_id}")
        for field_name in ("suite", "category", "language", "query_type"):
            value = getattr(query, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty: {query.query_id}")
        suites.add(query.suite)
        if query.language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language for {query.query_id}: {query.language}")
        if query.query_type not in SUPPORTED_QUERY_TYPES:
            raise ValueError(f"unsupported query_type for {query.query_id}: {query.query_type}")
        if not query.relevance:
            raise ValueError(f"relevance must not be empty: {query.query_id}")
        positive = False
        for chunk_id, grade in query.relevance.items():
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError(f"relevance chunk IDs must be non-empty strings: {query.query_id}")
            if isinstance(grade, bool) or not isinstance(grade, int) or grade < 0:
                raise ValueError(f"invalid relevance grade for {query.query_id}/{chunk_id}: {grade!r}")
            if chunk_id not in corpus_chunk_ids:
                raise ValueError(f"unknown gold chunk ID for {query.query_id}: {chunk_id}")
            positive = positive or grade > 0
        if not positive:
            raise ValueError(f"relevance must contain a positive grade: {query.query_id}")
    if len(suites) != 1:
        raise ValueError("all queries in an evaluation suite must use the same suite name")


def _row_to_chunk(row: dict[str, Any]) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=row["chunk_id"],
        source_type=row["source_type"],
        package=row["package"],
        function=row["function"],
        title=row["title"],
        text=row["text"],
        source_url=row["source_url"],
        license=row["license"],
        provenance=row["provenance"],
        priority=row["priority"],
        package_version=row.get("package_version"),
        published=row.get("published"),
    )


def build_cran_metadata_evaluation_corpus(
    fixture_dir: Path | None = None,
) -> list[KnowledgeChunk]:
    """Build the 16-chunk CRAN metadata corpus entirely from local HTML fixtures."""

    packages = crawl_packages(
        list(DEFAULT_PACKAGES),
        offline_html_dir=fixture_dir or DEFAULT_FIXTURE_DIR,
    )
    return [_row_to_chunk(row) for row in build_corpus_from_packages(packages)]


def load_evaluation_suite(
    path: Path,
    corpus_profile: str,
    cran_fixture_dir: Path | None = None,
) -> tuple[list[GoldQuery], list[KnowledgeChunk]]:
    if corpus_profile not in SUPPORTED_CORPUS_PROFILES:
        supported = ", ".join(sorted(SUPPORTED_CORPUS_PROFILES))
        raise ValueError(f"unsupported corpus profile {corpus_profile!r}; choose one of: {supported}")
    if corpus_profile == "fixture-core":
        corpus = load_corpus(path=DEFAULT_CORPUS_PATH)
    else:
        corpus = build_cran_metadata_evaluation_corpus(fixture_dir=cran_fixture_dir)
    queries = load_gold_queries(path)
    validate_gold_queries(queries, {chunk.chunk_id for chunk in corpus})
    return queries, corpus
