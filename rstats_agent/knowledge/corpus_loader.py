"""Load the small local JSONL knowledge corpus."""

from __future__ import annotations

import json
from pathlib import Path

from rstats_agent.config import DEFAULT_CORPUS_PATH, DEFAULT_PROCESSED_CORPUS_PATH
from rstats_agent.schemas import JsonObject, KnowledgeChunk


REQUIRED_FIELDS = {
    "chunk_id",
    "source_type",
    "package",
    "function",
    "title",
    "text",
    "source_url",
    "license",
    "provenance",
    "priority",
}

OPTIONAL_FIELDS = {
    "package_version",
    "published",
}


def _validate_record(record: JsonObject, line_number: int) -> None:
    missing = REQUIRED_FIELDS.difference(record)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Corpus line {line_number} is missing fields: {missing_text}")


def resolve_corpus_path(
    path: str | Path | None = None,
    processed_path: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> Path:
    """Resolve the preferred corpus path, preserving the v0.1 fixture fallback."""

    if path is not None:
        return Path(path)
    processed = Path(processed_path) if processed_path is not None else DEFAULT_PROCESSED_CORPUS_PATH
    if processed.exists():
        return processed
    return Path(fixture_path) if fixture_path is not None else DEFAULT_CORPUS_PATH


def identify_corpus_source(
    corpus_path: str | Path,
    processed_path: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> str:
    """Return a stable source label for report diagnostics."""

    path = Path(corpus_path)
    processed = Path(processed_path) if processed_path is not None else DEFAULT_PROCESSED_CORPUS_PATH
    fixture = Path(fixture_path) if fixture_path is not None else DEFAULT_CORPUS_PATH

    if path.exists() and processed.exists() and path.resolve() == processed.resolve():
        return "processed_corpus"
    if path.exists() and fixture.exists() and path.resolve() == fixture.resolve():
        return "fixture_fallback"
    return "custom_corpus"


def _record_to_chunk(record: JsonObject) -> KnowledgeChunk:
    data = {field: record[field] for field in REQUIRED_FIELDS}
    for field in OPTIONAL_FIELDS:
        data[field] = record.get(field)
    return KnowledgeChunk(**data)


def load_corpus(
    path: str | Path | None = None,
    processed_path: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> list[KnowledgeChunk]:
    """Load processed v0.2 corpus when present, otherwise fallback to v0.1 fixtures."""

    corpus_path = resolve_corpus_path(path=path, processed_path=processed_path, fixture_path=fixture_path)
    chunks: list[KnowledgeChunk] = []
    with corpus_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            _validate_record(record, line_number)
            chunks.append(_record_to_chunk(record))

    if not chunks:
        raise ValueError(f"Corpus is empty: {corpus_path}")
    return chunks


def load_corpus_with_metadata(
    path: str | Path | None = None,
    processed_path: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> tuple[list[KnowledgeChunk], str, Path]:
    """Load corpus chunks and return the selected source label and path."""

    corpus_path = resolve_corpus_path(path=path, processed_path=processed_path, fixture_path=fixture_path)
    chunks = load_corpus(path=corpus_path)
    knowledge_source = identify_corpus_source(
        corpus_path=corpus_path,
        processed_path=processed_path,
        fixture_path=fixture_path,
    )
    return chunks, knowledge_source, corpus_path
