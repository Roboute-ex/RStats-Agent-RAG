import math
import sys
import types

import pytest

from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.embeddings.sentence_transformer import SentenceTransformerEmbeddingBackend


def test_local_hash_embedding_is_stable_and_normalized():
    backend = LocalHashEmbeddingBackend(dimension=128)

    first = backend.embed_query("dplyr filter missing price")
    second = backend.embed_query("dplyr filter missing price")

    assert first == second
    assert len(first) == 128
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0, rel_tol=1e-9)


def test_local_hash_embedding_handles_empty_text():
    backend = LocalHashEmbeddingBackend(dimension=16)

    vector = backend.embed_query("")

    assert vector == [0.0] * 16


def test_sentence_transformer_backend_uses_encode_with_monkeypatch(monkeypatch):
    calls = {}

    class FakeModel:
        def __init__(self, model_name):
            calls["model_name"] = model_name

        def get_sentence_embedding_dimension(self):
            return 3

        def encode(self, texts, normalize_embeddings, convert_to_numpy):
            calls["texts"] = texts
            calls["normalize_embeddings"] = normalize_embeddings
            calls["convert_to_numpy"] = convert_to_numpy
            return [[1.0, 0.0, 0.0] for _ in texts]

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    backend = SentenceTransformerEmbeddingBackend(model_name="fake-model")

    assert backend.dimension == 3
    assert backend.embed_query("hello") == [1.0, 0.0, 0.0]
    assert calls["model_name"] == "fake-model"
    assert calls["texts"] == ["hello"]
    assert calls["normalize_embeddings"] is True
    assert calls["convert_to_numpy"] is False


def test_sentence_transformer_backend_missing_import_message(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    with pytest.raises(RuntimeError, match=r"\.\[vector\]"):
        SentenceTransformerEmbeddingBackend()
