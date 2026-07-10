"""Run the deterministic offline retrieval benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rstats_agent.evaluation.dataset import load_evaluation_suite
from rstats_agent.evaluation.evaluator import compare_retrievers
from rstats_agent.evaluation.regression import (
    compare_against_baseline,
    load_baseline,
    save_baseline,
)
from rstats_agent.evaluation.reporting import write_evaluation_json, write_evaluation_markdown


SUCCESS = 0
INVALID_CONFIGURATION = 2
REGRESSION_FAILED = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate local retrieval against a fixed gold suite.")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument(
        "--corpus-profile",
        choices=("fixture-core", "cran-metadata"),
        required=True,
    )
    parser.add_argument(
        "--retrievers",
        nargs="+",
        choices=("tfidf", "vector", "hybrid"),
        default=["tfidf", "vector", "hybrid"],
    )
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5])
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--hybrid-vector-weight", type=float, default=0.6)
    parser.add_argument("--hybrid-lexical-weight", type=float, default=0.4)
    parser.add_argument("--write-baseline", type=Path)
    parser.add_argument("--compare-baseline", type=Path)
    parser.add_argument("--max-regression", type=float, default=0.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def _print_summary(args: argparse.Namespace, summaries, json_path: Path, markdown_path: Path) -> None:
    if args.quiet:
        return
    print(f"Corpus profile: {args.corpus_profile}")
    print(f"Query count: {summaries[0].query_count}")
    print(f"Corpus chunk count: {summaries[0].metadata['corpus_chunk_count']}")
    max_k = max(summaries[0].k_values)
    for summary in summaries:
        recall = " ".join(
            f"Recall@{k}={summary.overall_metrics[f'recall@{k}']:.4f}"
            for k in summary.k_values
        )
        print(
            f"{summary.retriever}: {recall} "
            f"MRR@{max_k}={summary.overall_metrics[f'mrr@{max_k}']:.4f} "
            f"nDCG@{max_k}={summary.overall_metrics[f'ndcg@{max_k}']:.4f} "
            f"zero_hits={len(summary.zero_hit_queries)}"
        )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


def run(args: argparse.Namespace) -> int:
    if args.max_regression < 0:
        raise ValueError("--max-regression must be non-negative")
    if args.hybrid_vector_weight < 0 or args.hybrid_lexical_weight < 0:
        raise ValueError("hybrid weights must be non-negative")
    if args.hybrid_vector_weight == 0 and args.hybrid_lexical_weight == 0:
        raise ValueError("at least one hybrid weight must be positive")
    queries, corpus = load_evaluation_suite(args.suite, args.corpus_profile)
    summaries = compare_retrievers(
        queries,
        corpus,
        retriever_names=args.retrievers,
        corpus_profile=args.corpus_profile,
        k_values=args.k,
        hybrid_vector_weight=args.hybrid_vector_weight,
        hybrid_lexical_weight=args.hybrid_lexical_weight,
    )
    json_path = write_evaluation_json(summaries, args.output_dir / "retrieval_evaluation.json")
    markdown_path = write_evaluation_markdown(summaries, args.output_dir / "retrieval_evaluation.md")
    _print_summary(args, summaries, json_path, markdown_path)

    if args.write_baseline is not None:
        save_baseline(summaries, args.write_baseline, force=args.force)
        if not args.quiet:
            print(f"Baseline written: {args.write_baseline}")

    if args.compare_baseline is not None:
        baseline = load_baseline(args.compare_baseline)
        comparisons = [
            compare_against_baseline(summary, baseline, args.max_regression)
            for summary in summaries
        ]
        failures = [
            f"{summary.retriever}: {failure}"
            for summary, comparison in zip(summaries, comparisons, strict=True)
            for failure in comparison.failures
        ]
        if failures:
            if not args.quiet:
                print("Baseline regression status: FAILED")
                for failure in failures:
                    print(f"- {failure}")
            return REGRESSION_FAILED
        if not args.quiet:
            print("Baseline regression status: PASSED")
    return SUCCESS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INVALID_CONFIGURATION


if __name__ == "__main__":
    raise SystemExit(main())
