import json
from pathlib import Path

from data.build_corpus import build_corpus_from_packages, write_jsonl
from data.crawl_cran_packages import crawl_packages


FIXTURE_DIR = Path("data/raw/fixtures")
TEST_OUTPUT = Path(".test-output")


def test_build_corpus_from_packages_generates_expected_chunks():
    packages = crawl_packages(["dplyr", "ggplot2"], offline_html_dir=FIXTURE_DIR)

    rows = build_corpus_from_packages(packages)

    assert len(rows) == 8
    chunk_ids = {row["chunk_id"] for row in rows}
    assert "dplyr-cran-package-overview" in chunk_ids
    assert "dplyr-cran-reference-manual" in chunk_ids
    assert "dplyr-cran-vignettes-index" in chunk_ids
    assert "dplyr-cran-source-package" in chunk_ids
    assert all(row["provenance"] == "cran_package_page" for row in rows)
    assert all(row["package_version"] for row in rows)
    assert all(row["published"] for row in rows)
    assert {row["source_type"] for row in rows} >= {
        "cran_package_overview",
        "cran_reference_manual",
        "cran_vignettes_index",
        "cran_source_package",
    }


def test_write_jsonl_writes_one_json_object_per_line():
    packages = crawl_packages(["renv"], offline_html_dir=FIXTURE_DIR)
    rows = build_corpus_from_packages(packages)
    TEST_OUTPUT.mkdir(exist_ok=True)
    output = TEST_OUTPUT / "test-corpus.jsonl"

    write_jsonl(rows, output)

    loaded = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(loaded) == 4
    assert loaded[0]["package"] == "renv"
