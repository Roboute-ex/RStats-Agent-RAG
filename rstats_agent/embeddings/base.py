"""Small embedding backend protocol used by vector index builders."""

from __future__ import annotations

from typing import Protocol


class EmbeddingBackend(Protocol):
    name: str
    dimension: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts as dense float vectors."""

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query as a dense float vector."""
