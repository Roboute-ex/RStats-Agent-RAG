"""Collect and parse CRAN package page metadata.

Tests use local HTML fixtures only. Real network fetching is available for
manual script runs, not for the deterministic test suite.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_PACKAGES = ["dplyr", "ggplot2", "lme4", "renv"]
DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parent / "raw" / "fixtures"


def build_cran_package_url(pkg: str) -> str:
    return f"https://CRAN.R-project.org/package={pkg}"


def fetch_cran_package_page(pkg: str, timeout_sec: int = 30) -> str:
    response = requests.get(build_cran_package_url(pkg), timeout=timeout_sec)
    response.raise_for_status()
    return response.text


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _text(node: Any | None) -> str | None:
    if node is None:
        return None
    value = node.get_text(" ", strip=True)
    return value or None


def _table_metadata(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        key = _normalize_key(_text(cells[0]) or "")
        value = _text(cells[1])
        if key and value:
            metadata[key] = value
    return metadata


def _absolute_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base_url, href)


def _find_link_url(soup: BeautifulSoup, source_url: str, predicate: Any) -> str | None:
    for link in soup.find_all("a", href=True):
        href = str(link.get("href", ""))
        label = _text(link) or ""
        if predicate(href.lower(), label.lower()):
            return _absolute_url(source_url, href)
    return None


def _parse_vignettes(soup: BeautifulSoup, source_url: str) -> list[dict[str, str | None]]:
    vignettes: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for row in soup.find_all("tr"):
        links = row.find_all("a", href=True)
        if not any("/vignettes/" in str(link.get("href", "")).lower() for link in links):
            continue

        title = None
        html_url = None
        source_doc_url = None
        r_code_url = None
        for link in links:
            href = str(link.get("href", ""))
            href_lower = href.lower()
            label = _text(link)
            if "/vignettes/" not in href_lower:
                continue
            absolute = _absolute_url(source_url, href)
            if href_lower.endswith(".html") and html_url is None:
                html_url = absolute
                title = label or title
            elif href_lower.endswith((".rmd", ".qmd", ".rnw")) and source_doc_url is None:
                source_doc_url = absolute
            elif href_lower.endswith(".r") and r_code_url is None:
                r_code_url = absolute

        if html_url and html_url not in seen:
            seen.add(html_url)
            vignettes.append(
                {
                    "title": title or _text(row) or "Vignette",
                    "html_url": html_url,
                    "source_url": source_doc_url,
                    "r_code_url": r_code_url,
                }
            )
    return vignettes


def parse_cran_package_page(html: str, package: str, source_url: str) -> dict[str, Any]:
    """Parse a CRAN package page into tolerant metadata fields."""

    soup = BeautifulSoup(html, "html.parser")
    metadata = _table_metadata(soup)

    reference_manual_html = _find_link_url(
        soup,
        source_url,
        lambda href, label: ("reference manual" in label or "/manual/" in href) and href.endswith(".html"),
    )
    reference_manual_pdf = _find_link_url(
        soup,
        source_url,
        lambda href, label: ("reference manual" in label or href.endswith(f"/{package.lower()}.pdf"))
        and href.endswith(".pdf"),
    )
    package_source_url = _find_link_url(
        soup,
        source_url,
        lambda href, label: href.endswith(".tar.gz") and "/src/contrib/" in href and "/archive/" not in href,
    )
    old_sources_url = _find_link_url(
        soup,
        source_url,
        lambda href, label: f"/archive/{package.lower()}" in href or "old sources" in label,
    )

    return {
        "package": metadata.get("package") or package,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "version": metadata.get("version"),
        "published": metadata.get("published"),
        "license": metadata.get("license"),
        "depends": metadata.get("depends"),
        "imports": metadata.get("imports"),
        "suggests": metadata.get("suggests"),
        "url": metadata.get("url"),
        "bug_reports": metadata.get("bugreports") or metadata.get("bug_reports"),
        "reference_manual_html": reference_manual_html,
        "reference_manual_pdf": reference_manual_pdf,
        "vignettes": _parse_vignettes(soup, source_url),
        "package_source_url": package_source_url,
        "old_sources_url": old_sources_url,
        "source_url": source_url,
        "provenance": "cran_package_page",
    }


def crawl_packages(packages: list[str], offline_html_dir: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for package in packages:
        source_url = build_cran_package_url(package)
        if offline_html_dir is not None:
            html = (offline_html_dir / f"cran_{package}.html").read_text(encoding="utf-8")
            captured_at = "offline_fixture"
        else:
            html = fetch_cran_package_page(package)
            captured_at = datetime.now(UTC).isoformat(timespec="seconds")
        row = parse_cran_package_page(html=html, package=package, source_url=source_url)
        row["captured_at"] = captured_at
        rows.append(row)
    return rows


def save_raw_packages(packages: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packages, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect CRAN package metadata for v0.2 corpus building.")
    parser.add_argument("--packages", nargs="+", default=DEFAULT_PACKAGES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--offline-fixtures",
        action="store_true",
        help="Use local data/raw/fixtures HTML instead of network requests.",
    )
    parser.add_argument("--offline-html-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    offline_dir = args.offline_html_dir if args.offline_fixtures else None
    rows = crawl_packages(packages=args.packages, offline_html_dir=offline_dir)
    save_raw_packages(rows, args.output)
    print(f"Wrote {len(rows)} package metadata rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
