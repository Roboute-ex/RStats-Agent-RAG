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
    repair: bool = False
    max_repairs: int = 1
    timeout_sec: int = 20
    docker_image: str = "rocker/r-ver:4.3.3"


@dataclass
class ExecutionResult:
    status: str = "skipped"
    ok: bool | None = None
    skipped: bool | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    reason: str | None = None
    timed_out: bool = False
    duration_sec: float | None = None
    command_preview: list[str] | None = None
    diagnostics: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        status_aliases = {
            "success": "ok",
            "blocked": "unsafe",
        }
        if self.status in status_aliases:
            self.status = status_aliases[self.status]
        if self.ok is None:
            self.ok = self.status == "ok"
        if self.skipped is None:
            self.skipped = self.status == "skipped"


@dataclass
class ExecutionDiagnostic:
    error_type: str
    severity: str
    message: str
    evidence: str
    likely_cause: str
    suggested_fix: str


@dataclass
class RepairSuggestion:
    repair_type: str
    message: str
    patched_code: str | None = None
    confidence: str = "low"
    applied: bool = False


@dataclass
class RepairLoopResult:
    original_code: str
    original_execution: ExecutionResult
    diagnostics: list[ExecutionDiagnostic] = field(default_factory=list)
    suggestions: list[RepairSuggestion] = field(default_factory=list)
    repaired_code: str | None = None
    repaired_execution: ExecutionResult | None = None
    attempts: int = 0


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
    execution_diagnostics: list[ExecutionDiagnostic] = field(default_factory=list)
    repair_suggestions: list[RepairSuggestion] = field(default_factory=list)
    repair_loop: RepairLoopResult | None = None


@dataclass
class ReportResult:
    markdown: str
    path: Path | None = None
    diagnostics: list[str] = field(default_factory=list)


JsonObject = dict[str, Any]
