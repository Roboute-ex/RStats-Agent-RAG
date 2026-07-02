from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.knowledge.corpus_loader import load_corpus
from rstats_agent.knowledge.hybrid_retriever import HybridRetriever
from rstats_agent.knowledge.retriever import LocalTfidfRetriever
from rstats_agent.knowledge.vector_index import NumpyVectorIndex
from rstats_agent.config import DEFAULT_CORPUS_PATH


def test_hybrid_retriever_falls_back_to_tfidf_without_vector_index():
    chunks = load_corpus(DEFAULT_CORPUS_PATH)
    tfidf = LocalTfidfRetriever(chunks)
    hybrid = HybridRetriever(tfidf_retriever=tfidf)

    results = hybrid.search("dplyr filter missing price", top_k=3)

    assert results
    assert all(result.retriever == "tfidf" for result in results)
    assert "hybrid_retriever_fallback=tfidf" in hybrid.diagnostics


def test_hybrid_retriever_merges_vector_and_tfidf_scores():
    chunks = load_corpus(DEFAULT_CORPUS_PATH)
    tfidf = LocalTfidfRetriever(chunks)
    backend = LocalHashEmbeddingBackend()
    embeddings = backend.embed_texts([chunk.text for chunk in chunks])
    vector_index = NumpyVectorIndex.build(chunks, embeddings)
    hybrid = HybridRetriever(tfidf_retriever=tfidf, embedding_backend=backend, vector_index=vector_index)

    results = hybrid.search("lme4 random effects lmer sleepstudy", top_k=5)

    assert results
    assert results[0].retriever == "hybrid"
    assert any(result.vector_score is not None for result in results)
    assert any(result.lexical_score is not None for result in results)
    assert "hybrid_retriever_used=vector+tfidf" in hybrid.diagnostics
