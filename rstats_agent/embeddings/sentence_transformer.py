"""Optional sentence-transformers embedding backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


INSTALL_HINT = 'sentence-transformers is not installed. Install vector extras with: py -3 -m pip install -e ".[vector]"'


@dataclass
class SentenceTransformerEmbeddingBackend:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    normalize_embeddings: bool = True
    name: str = "sentence-transformer"
    model: Any = field(init=False, repr=False)
    dimension: int = field(init=False)

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(INSTALL_HINT) from exc

        self.model = SentenceTransformer(self.model_name)
        dimension = None
        if hasattr(self.model, "get_sentence_embedding_dimension"):
            dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None:
            probe = self.embed_query("")
            dimension = len(probe)
        self.dimension = int(dimension)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=False,
        )
        return [list(map(float, vector)) for vector in vectors]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
