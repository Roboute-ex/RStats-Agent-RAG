from pathlib import Path
from uuid import uuid4

from data.build_vector_index import main


TEST_OUTPUT = Path(".test-output")


def _output_dir(name: str) -> Path:
    TEST_OUTPUT.mkdir(exist_ok=True)
    return TEST_OUTPUT / f"{uuid4().hex}-{name}"


def test_build_vector_index_local_hash_numpy_from_fixture_corpus():
    output_dir = _output_dir("build-vector-index")
    corpus = Path("rstats_agent/knowledge/fixtures/r_core_corpus.jsonl")

    exit_code = main(
        [
            "--corpus",
            str(corpus),
            "--backend",
            "local-hash",
            "--index-backend",
            "numpy",
            "--output-dir",
            str(output_dir),
            "--query",
            "dplyr filter missing price group_by summarise revenue",
            "--top-k",
            "3",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "embeddings.npy").exists()
    assert (output_dir / "metadata.jsonl").exists()
