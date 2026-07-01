"""Build a processed JSONL corpus from parsed CRAN package metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _clean(value: Any) -> str:
    if value in (None, ""):
        return "Not available"
    return str(value)


def _base_chunk(package: dict[str, Any], suffix: str, source_type: str, title: str) -> dict[str, Any]:
    pkg = package["package"]
    return {
        "chunk_id": f"{pkg}-cran-{suffix}",
        "package": pkg,
        "function": "__package__",
        "source_type": source_type,
        "title": title,
        "source_url": package.get("source_url"),
        "license": package.get("license"),
        "provenance": package.get("provenance", "cran_package_page"),
        "priority": "P0",
        "package_version": package.get("version"),
        "published": package.get("published"),
    }


def build_corpus_from_packages(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for package in packages:
        pkg = package["package"]
        overview = _base_chunk(
            package,
            "package-overview",
            "cran_package_overview",
            f"{pkg} CRAN package overview",
        )
        overview["text"] = (
            f"{pkg} {package.get('version') or ''}: {_clean(package.get('title'))}. "
            f"{_clean(package.get('description'))} "
            f"Depends: {_clean(package.get('depends'))}. Imports: {_clean(package.get('imports'))}. "
            f"Suggests: {_clean(package.get('suggests'))}."
        )
        rows.append(overview)

        manual = _base_chunk(
            package,
            "reference-manual",
            "cran_reference_manual",
            f"{pkg} CRAN reference manual",
        )
        manual["function"] = "reference_manual"
        manual["source_url"] = package.get("reference_manual_html") or package.get("reference_manual_pdf")
        manual["text"] = (
            f"CRAN reference manual entry for {pkg}. "
            f"HTML: {_clean(package.get('reference_manual_html'))}. "
            f"PDF: {_clean(package.get('reference_manual_pdf'))}."
        )
        rows.append(manual)

        vignettes = package.get("vignettes") or []
        vignette_titles = ", ".join(vignette.get("title") or "Untitled" for vignette in vignettes) or "No vignettes listed"
        vignette_chunk = _base_chunk(
            package,
            "vignettes-index",
            "cran_vignettes_index",
            f"{pkg} CRAN vignettes index",
        )
        vignette_chunk["function"] = "vignettes_index"
        vignette_chunk["source_url"] = vignettes[0].get("html_url") if vignettes else package.get("source_url")
        vignette_chunk["priority"] = "P0" if vignettes else "P1"
        vignette_chunk["text"] = f"CRAN lists {len(vignettes)} vignette(s) for {pkg}: {vignette_titles}."
        rows.append(vignette_chunk)

        source_chunk = _base_chunk(
            package,
            "source-package",
            "cran_source_package",
            f"{pkg} CRAN source package",
        )
        source_chunk["function"] = "source_package"
        source_chunk["source_url"] = package.get("package_source_url")
        source_chunk["priority"] = "P1"
        source_chunk["text"] = (
            f"CRAN source package metadata for {pkg}. "
            f"Source tarball: {_clean(package.get('package_source_url'))}. "
            f"Old sources: {_clean(package.get('old_sources_url'))}."
        )
        rows.append(source_chunk)
    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build processed CRAN corpus JSONL.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packages = json.loads(args.input.read_text(encoding="utf-8"))
    rows = build_corpus_from_packages(packages)
    write_jsonl(rows, args.output)
    print(f"Wrote {len(rows)} corpus chunks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
