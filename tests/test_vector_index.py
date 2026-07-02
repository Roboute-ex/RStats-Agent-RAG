import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import pytest

from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.knowledge.vector_index import FaissVectorIndex, NumpyVectorIndex
from rstats_agent.schemas import KnowledgeChunk


TEST_OUTPUT = Path(".test-output")


def _output_path(name: str) -> Path:
    TEST_OUTPUT.mkdir(exist_ok=True)
    return TEST_OUTPUT / f"{uuid4().hex}-{name}"


def _chunk(chunk_id: str, package: str, text: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        source_type="test",
        package=package,
        function="__package__",
        title=chunk_id,
        text=text,
        source_url="https://example.test",
        license="synthetic_fixture",
        provenance="test",
        priority="P0",
    )


def _sample_chunks():
    return [
        _chunk("dplyr-filter", "dplyr", "dplyr filter missing price group_by summarise revenue"),
        _chunk("ggplot2-point", "ggplot2", "ggplot2 scatter plot geom_point color facet"),
        _chunk("lme4-lmer", "lme4", "lme4 lmer random effects sleepstudy subject"),
    ]


def test_numpy_vector_index_search_ranks_similar_text_first():
    backend = LocalHashEmbeddingBackend()
    chunks = _sample_chunks()
    embeddings = backend.embed_texts([chunk.text for chunk in chunks])
    index = NumpyVectorIndex.build(chunks, embeddings)

    results = index.search(backend.embed_query("dplyr price revenue summarise"), top_k=2)

    assert len(results) == 2
    assert results[0].chunk_id == "dplyr-filter"
    assert results[0].retriever == "vector"
    assert results[0].vector_score is not None


def test_numpy_vector_index_save_load_is_stable():
    backend = LocalHashEmbeddingBackend()
    chunks = _sample_chunks()
    embeddings = backend.embed_texts([chunk.text for chunk in chunks])
    index = NumpyVectorIndex.build(chunks, embeddings)
    index_path = _output_path("vector-index-embeddings.npy")
    metadata_path = _output_path("vector-index-metadata.jsonl")

    index.save(index_path, metadata_path)
    loaded = NumpyVectorIndex.load(index_path, metadata_path)

    original = index.search(backend.embed_query("lme4 random effects"), top_k=1)
    reloaded = loaded.search(backend.embed_query("lme4 random effects"), top_k=1)
    assert reloaded[0].chunk_id == original[0].chunk_id
    assert json.loads(metadata_path.read_text(encoding="utf-8").splitlines()[0])["chunk_id"] == "dplyr-filter"


def test_faiss_vector_index_optional_behavior():
    backend = LocalHashEmbeddingBackend()
    chunks = _sample_chunks()
    embeddings = backend.embed_texts([chunk.text for chunk in chunks])

    if importlib.util.find_spec("faiss") is None:
        with pytest.raises(RuntimeError, match=r"\.\[vector\]"):
            FaissVectorIndex.build(chunks, embeddings)
    else:
        index = FaissVectorIndex.build(chunks, embeddings)
        results = index.search(backend.embed_query("sleepstudy random effects"), top_k=1)
        assert results[0].chunk_id == "lme4-lmer"
