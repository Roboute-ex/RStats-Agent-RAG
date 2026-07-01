"""Build a JSONL license ledger from CRAN package metadata."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_license_ledger(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for package in packages:
        pkg = package["package"]
        rows.append(
            {
                "package": pkg,
                "package_version": package.get("version"),
                "license": package.get("license"),
                "source_url": package.get("source_url"),
                "attribution": f"Metadata captured from CRAN package page for {pkg}.",
                "provenance": package.get("provenance", "cran_package_page"),
                "published": package.get("published"),
                "captured_at": package.get("captured_at")
                or datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CRAN license ledger JSONL.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packages = json.loads(args.input.read_text(encoding="utf-8"))
    rows = build_license_ledger(packages)
    write_jsonl(rows, args.output)
    print(f"Wrote {len(rows)} license rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
