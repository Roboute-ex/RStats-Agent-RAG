"""Dataclasses shared across the local Agent/RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source_type: str
    package: str
    function: str
    title: str
    text: str
    source_url: str
    license: str
    provenance: str
    priority: str
    package_version: str | None = None
    published: str | None = None


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    source_type: str
    package: str
    function: str
    title: str
    text: str
    source_url: str
    license: str
    provenance: str
    priority: str
    score: float
    package_version: str | None = None
    published: str | None = None
    retriever: str = "tfidf"
    vector_score: float | None = None
    lexical_score: float | None = None

    @classmethod
    def from_chunk(cls, chunk: KnowledgeChunk, score: float) -> "RetrievalResult":
        return cls(
            chunk_id=chunk.chunk_id,
            source_type=chunk.source_type,
            package=chunk.package,
            function=chunk.function,
            title=chunk.title,
            text=chunk.text,
            source_url=chunk.source_url,
            license=chunk.license,
            provenance=chunk.provenance,
            priority=chunk.priority,
            score=score,
            package_version=chunk.package_version,
            published=chunk.published,
            retriever="tfidf",
            lexical_score=score,
        )

    def as_citation(self) -> str:
        return f"{self.chunk_id} ({self.package}::{self.function})"


@dataclass(frozen=True)
class AgentRequest:
    question: str
    top_k: int = 6
    execute: bool = False
    retriever: str = "tfidf"


@dataclass
class ExecutionResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    question: str
    task_type: str
    rewritten_queries: dict[str, str]
    retrieved: list[RetrievalResult]
    context: list[RetrievalResult]
    r_code: str
    explanation: str
    assumptions: list[str]
    failure_modes: list[str]
    citations: list[str]
    execution: ExecutionResult
    knowledge_source: str = "unknown"
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class ReportResult:
    markdown: str
    path: Path | None = None
    diagnostics: list[str] = field(default_factory=list)


JsonObject = dict[str, Any]
