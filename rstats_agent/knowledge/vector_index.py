"""Local vector indexes for dense retrieval."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from rstats_agent.schemas import KnowledgeChunk, RetrievalResult


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix.astype("float32")
    matrix = matrix.astype("float32", copy=False)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


def _normalize_vector(vector: list[float]) -> np.ndarray:
    array = np.asarray(vector, dtype="float32")
    norm = float(np.linalg.norm(array))
    if norm == 0.0:
        return array
    return array / norm


def _metadata_to_chunk(row: dict) -> KnowledgeChunk:
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


def _write_metadata(chunks: list[KnowledgeChunk], metadata_path: Path) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.unlink(missing_ok=True)
    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False, sort_keys=True) + "\n")


def _read_metadata(metadata_path: Path) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    with metadata_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                chunks.append(_metadata_to_chunk(json.loads(stripped)))
    return chunks


class VectorIndex(Protocol):
    chunks: list[KnowledgeChunk]

    @classmethod
    def build(cls, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> "VectorIndex":
        """Build an index from chunks and dense embeddings."""

    def search(self, query_embedding: list[float], top_k: int = 6) -> list[RetrievalResult]:
        """Search dense vectors and return retrieval results."""

    def save(self, index_path: Path, metadata_path: Path) -> None:
        """Persist vector index files."""

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "VectorIndex":
        """Load vector index files."""


@dataclass
class NumpyVectorIndex:
    chunks: list[KnowledgeChunk]
    embeddings: np.ndarray

    @classmethod
    def build(cls, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> "NumpyVectorIndex":
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        matrix = np.asarray(embeddings, dtype="float32")
        if matrix.ndim != 2:
            raise ValueError("embeddings must be a 2D matrix")
        return cls(chunks=list(chunks), embeddings=_normalize_matrix(matrix))

    def search(self, query_embedding: list[float], top_k: int = 6) -> list[RetrievalResult]:
        if not self.chunks:
            return []
        query = _normalize_vector(query_embedding)
        scores = self.embeddings @ query
        order = sorted(
            range(len(self.chunks)),
            key=lambda index: (-float(scores[index]), self.chunks[index].chunk_id),
        )[:top_k]
        results = [
            RetrievalResult.from_chunk(self.chunks[int(index)], float(scores[int(index)]))
            for index in order
        ]
        for result in results:
            object.__setattr__(result, "retriever", "vector")
            object.__setattr__(result, "vector_score", result.score)
            object.__setattr__(result, "lexical_score", None)
        return sorted(results, key=lambda result: (-result.score, result.chunk_id))

    def save(self, index_path: Path, metadata_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.unlink(missing_ok=True)
        np.save(index_path, self.embeddings)
        _write_metadata(self.chunks, metadata_path)

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "NumpyVectorIndex":
        return cls(chunks=_read_metadata(metadata_path), embeddings=np.load(index_path))


@dataclass
class FaissVectorIndex:
    chunks: list[KnowledgeChunk]
    index: object

    @staticmethod
    def _import_faiss():
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError('faiss-cpu is not installed. Install vector extras with: py -3 -m pip install -e ".[vector]"') from exc
        return faiss

    @classmethod
    def build(cls, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> "FaissVectorIndex":
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        faiss = cls._import_faiss()
        matrix = _normalize_matrix(np.asarray(embeddings, dtype="float32"))
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(chunks=list(chunks), index=index)

    def search(self, query_embedding: list[float], top_k: int = 6) -> list[RetrievalResult]:
        if not self.chunks:
            return []
        query = _normalize_vector(query_embedding).reshape(1, -1)
        scores, indices = self.index.search(query, min(top_k, len(self.chunks)))
        results: list[RetrievalResult] = []
        for score, index in zip(scores[0], indices[0], strict=False):
            if int(index) < 0:
                continue
            result = RetrievalResult.from_chunk(self.chunks[int(index)], float(score))
            object.__setattr__(result, "retriever", "vector")
            object.__setattr__(result, "vector_score", result.score)
            object.__setattr__(result, "lexical_score", None)
            results.append(result)
        return sorted(results, key=lambda result: (-result.score, result.chunk_id))

    def save(self, index_path: Path, metadata_path: Path) -> None:
        faiss = self._import_faiss()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.unlink(missing_ok=True)
        faiss.write_index(self.index, str(index_path))
        _write_metadata(self.chunks, metadata_path)

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "FaissVectorIndex":
        faiss = cls._import_faiss()
        return cls(chunks=_read_metadata(metadata_path), index=faiss.read_index(str(index_path)))
