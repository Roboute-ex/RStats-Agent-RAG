from rstats_agent.knowledge.corpus_loader import load_corpus


def test_loads_fixture_corpus_with_required_chunks():
    chunks = load_corpus()

    assert len(chunks) >= 12
    chunk_ids = {chunk.chunk_id for chunk in chunks}
    assert "dplyr-filter" in chunk_ids
    assert "ggplot2-geom-point" in chunk_ids
    assert "lme4-sleepstudy-example" in chunk_ids
    assert all(chunk.priority in {"P0", "P1", "P2"} for chunk in chunks)
    assert all(chunk.license == "synthetic_fixture" for chunk in chunks)
    assert all(chunk.provenance == "handwritten_summary_for_offline_tests" for chunk in chunks)
