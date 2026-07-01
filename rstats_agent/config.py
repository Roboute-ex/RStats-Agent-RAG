"""Project-level configuration and filesystem paths."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_CORPUS_PATH = PACKAGE_ROOT / "knowledge" / "fixtures" / "r_core_corpus.jsonl"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_TOP_K = 6
