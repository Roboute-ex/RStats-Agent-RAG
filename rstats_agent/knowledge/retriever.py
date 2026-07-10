"""Local TF-IDF retriever over the fixture knowledge corpus."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rstats_agent.config import DEFAULT_TOP_K
from rstats_agent.knowledge.corpus_loader import load_corpus, load_corpus_with_metadata
from rstats_agent.knowledge.query_rewriter import rewrite_query
from rstats_agent.schemas import KnowledgeChunk, RetrievalResult


PRIORITY_BONUS = {"P0": 0.03, "P1": 0.015, "P2": 0.0}


@dataclass
class LocalTfidfRetriever:
    chunks: list[KnowledgeChunk]
    knowledge_source: str = "custom_corpus"
    corpus_path: Path | None = None
    vectorizer: TfidfVectorizer = field(init=False)
    matrix: object = field(init=False)

    def __post_init__(self) -> None:
        documents = [self._document_text(chunk) for chunk in self.chunks]
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[\w\.\|~]+\b",
        )
        self.matrix = self.vectorizer.fit_transform(documents)

    @staticmethod
    def _document_text(chunk: KnowledgeChunk) -> str:
        return " ".join(
            [
                chunk.chunk_id,
                chunk.package,
                chunk.function,
                chunk.source_type,
                chunk.title,
                chunk.text,
                chunk.priority,
            ]
        )

    @staticmethod
    def _combine_query(query: str | dict[str, str]) -> str:
        if isinstance(query, str):
            return " ".join(rewrite_query(query).values())
        return " ".join(query.values())

    @staticmethod
    def _metadata_bonus(chunk: KnowledgeChunk, query_text: str) -> float:
        lowered = query_text.lower()
        bonus = PRIORITY_BONUS.get(chunk.priority, 0.0)
        if chunk.package.lower() in lowered:
            bonus += 0.15
        function_tokens = {chunk.function.lower(), chunk.function.lower().replace("_", " ")}
        if any(token and token in lowered for token in function_tokens):
            bonus += 0.08
        return bonus

    def search(self, query: str | dict[str, str], top_k: int = DEFAULT_TOP_K) -> list[RetrievalResult]:
        """Return top-k chunks sorted by weighted score, without a hard threshold."""

        query_text = self._combine_query(query)
        query_vector = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vector, self.matrix).ravel()
        results = [
            RetrievalResult.from_chunk(
                chunk,
                float(similarities[index]) + self._metadata_bonus(chunk, query_text),
            )
            for index, chunk in enumerate(self.chunks)
        ]
        results.sort(key=lambda item: (-item.score, item.chunk_id))
        return results[:top_k]


def build_default_retriever() -> LocalTfidfRetriever:
    chunks, knowledge_source, corpus_path = load_corpus_with_metadata()
    return LocalTfidfRetriever(
        chunks=chunks,
        knowledge_source=knowledge_source,
        corpus_path=corpus_path,
    )
