"""Load the small local JSONL knowledge corpus."""

from __future__ import annotations

import json
from pathlib import Path

from rstats_agent.config import DEFAULT_CORPUS_PATH
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


def _validate_record(record: JsonObject, line_number: int) -> None:
    missing = REQUIRED_FIELDS.difference(record)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Corpus line {line_number} is missing fields: {missing_text}")


def load_corpus(path: str | Path | None = None) -> list[KnowledgeChunk]:
    """Load fixture chunks from JSONL and validate the expected v0.1 schema."""

    corpus_path = Path(path) if path is not None else DEFAULT_CORPUS_PATH
    chunks: list[KnowledgeChunk] = []
    with corpus_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            _validate_record(record, line_number)
            chunks.append(KnowledgeChunk(**{field: record[field] for field in REQUIRED_FIELDS}))

    if not chunks:
        raise ValueError(f"Corpus is empty: {corpus_path}")
    return chunks
