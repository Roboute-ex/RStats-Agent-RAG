import json
from pathlib import Path

from data.build_license_ledger import build_license_ledger, write_jsonl
from data.crawl_cran_packages import crawl_packages


FIXTURE_DIR = Path("data/raw/fixtures")
TEST_OUTPUT = Path(".test-output")


def test_build_license_ledger_generates_license_rows():
    packages = crawl_packages(["lme4", "renv"], offline_html_dir=FIXTURE_DIR)

    rows = build_license_ledger(packages)

    assert len(rows) == 2
    assert rows[0]["package"] == "lme4"
    assert rows[0]["license"] == "GPL (>= 2)"
    assert rows[0]["attribution"] == "Metadata captured from CRAN package page for lme4."
    assert rows[0]["provenance"] == "cran_package_page"
    assert rows[0]["captured_at"] == "offline_fixture"


def test_write_license_ledger_jsonl():
    packages = crawl_packages(["dplyr"], offline_html_dir=FIXTURE_DIR)
    rows = build_license_ledger(packages)
    TEST_OUTPUT.mkdir(exist_ok=True)
    output = TEST_OUTPUT / "test-licenses.jsonl"

    write_jsonl(rows, output)

    loaded = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert loaded[0]["package"] == "dplyr"
    assert loaded[0]["package_version"] == "1.1.4"
