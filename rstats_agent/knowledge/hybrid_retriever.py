"""Hybrid retriever combining TF-IDF and optional dense vector results."""

from __future__ import annotations

from dataclasses import dataclass, field

from rstats_agent.embeddings.base import EmbeddingBackend
from rstats_agent.knowledge.retriever import LocalTfidfRetriever
from rstats_agent.knowledge.vector_index import VectorIndex
from rstats_agent.schemas import RetrievalResult


@dataclass
class HybridRetriever:
    tfidf_retriever: LocalTfidfRetriever
    embedding_backend: EmbeddingBackend | None = None
    vector_index: VectorIndex | None = None
    diagnostics: list[str] = field(default_factory=list)
    knowledge_source: str = field(init=False)

    def __post_init__(self) -> None:
        self.knowledge_source = self.tfidf_retriever.knowledge_source

    def search(self, query: str | dict[str, str], top_k: int = 6) -> list[RetrievalResult]:
        tfidf_results = self.tfidf_retriever.search(query, top_k=top_k)
        if self.embedding_backend is None or self.vector_index is None:
            self.diagnostics.append("hybrid_retriever_fallback=tfidf")
            return tfidf_results

        query_text = LocalTfidfRetriever._combine_query(query)
        vector_results = self.vector_index.search(self.embedding_backend.embed_query(query_text), top_k=top_k)

        merged: dict[str, RetrievalResult] = {}
        lexical_scores = {result.chunk_id: result.score for result in tfidf_results}
        vector_scores = {result.chunk_id: result.score for result in vector_results}
        all_ids = set(lexical_scores).union(vector_scores)
        by_id = {result.chunk_id: result for result in [*tfidf_results, *vector_results]}

        for chunk_id in all_ids:
            lexical_score = lexical_scores.get(chunk_id, 0.0)
            vector_score = vector_scores.get(chunk_id, 0.0)
            final_score = 0.6 * vector_score + 0.4 * lexical_score
            base = by_id[chunk_id]
            result = RetrievalResult(
                chunk_id=base.chunk_id,
                source_type=base.source_type,
                package=base.package,
                function=base.function,
                title=base.title,
                text=base.text,
                source_url=base.source_url,
                license=base.license,
                provenance=base.provenance,
                priority=base.priority,
                score=final_score,
                package_version=base.package_version,
                published=base.published,
                retriever="hybrid",
                vector_score=vector_scores.get(chunk_id),
                lexical_score=lexical_scores.get(chunk_id),
            )
            merged[chunk_id] = result

        results = sorted(merged.values(), key=lambda result: result.score, reverse=True)[:top_k]
        self.diagnostics.append("hybrid_retriever_used=vector+tfidf")
        return results
