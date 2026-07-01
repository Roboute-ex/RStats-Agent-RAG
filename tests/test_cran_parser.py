from pathlib import Path

from data.crawl_cran_packages import build_cran_package_url, crawl_packages, parse_cran_package_page


FIXTURE_DIR = Path("data/raw/fixtures")


def test_parse_cran_package_page_extracts_expected_metadata():
    source_url = build_cran_package_url("dplyr")
    html = (FIXTURE_DIR / "cran_dplyr.html").read_text(encoding="utf-8")

    row = parse_cran_package_page(html, package="dplyr", source_url=source_url)

    assert row["package"] == "dplyr"
    assert row["version"] == "1.1.4"
    assert row["license"] == "MIT + file LICENSE"
    assert row["reference_manual_html"].endswith("/web/packages/dplyr/manual/dplyr.html")
    assert row["reference_manual_pdf"].endswith("/web/packages/dplyr/dplyr.pdf")
    assert row["package_source_url"].endswith("/src/contrib/dplyr_1.1.4.tar.gz")
    assert row["old_sources_url"].endswith("/src/contrib/Archive/dplyr/")
    assert row["vignettes"][0]["title"] == "dplyr"
    assert row["vignettes"][0]["html_url"].endswith("/web/packages/dplyr/vignettes/dplyr.html")
    assert row["vignettes"][0]["source_url"].endswith("/web/packages/dplyr/vignettes/dplyr.Rmd")
    assert row["vignettes"][0]["r_code_url"].endswith("/web/packages/dplyr/vignettes/dplyr.R")
    assert row["provenance"] == "cran_package_page"


def test_crawl_packages_uses_offline_fixtures_without_network():
    rows = crawl_packages(["dplyr", "renv"], offline_html_dir=FIXTURE_DIR)

    assert [row["package"] for row in rows] == ["dplyr", "renv"]
    assert all(row["captured_at"] == "offline_fixture" for row in rows)
