"""Command line demo entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.config import DEFAULT_VECTOR_ARTIFACTS_DIR
from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.execution.r_executor import DEFAULT_R_DOCKER_IMAGE
from rstats_agent.knowledge.hybrid_retriever import HybridRetriever
from rstats_agent.knowledge.retriever import build_default_retriever
from rstats_agent.knowledge.vector_index import NumpyVectorIndex
from rstats_agent.reporting.markdown import render_markdown_report, write_markdown_report
from rstats_agent.schemas import AgentRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RStats-Agent-RAG local demo")
    parser.add_argument("question", help="Chinese or English R statistics task request")
    parser.add_argument("--top-k", type=int, default=6, help="Number of retrieved knowledge chunks, default 6")
    parser.add_argument(
        "--retriever",
        choices=["tfidf", "hybrid"],
        default="tfidf",
        help="Retrieval mode. hybrid uses local vector artifacts when available and falls back to TF-IDF.",
    )
    parser.add_argument("--execute", action="store_true", help="Try optional Docker/R execution for generated R code")
    parser.add_argument(
        "--no-execute",
        dest="execute",
        action="store_false",
        help="Compatibility flag: explicitly keep R execution disabled",
    )
    parser.add_argument("--repair", action="store_true", help="Enable v0.4 rule-based repair suggestions")
    parser.add_argument("--max-repairs", type=int, default=1, help="Maximum repair attempts, default 1")
    parser.add_argument("--timeout-sec", type=int, default=20, help="Optional Docker/R execution timeout, default 20")
    parser.add_argument(
        "--docker-image",
        default=DEFAULT_R_DOCKER_IMAGE,
        help=f"Optional Docker/R image, default {DEFAULT_R_DOCKER_IMAGE}",
    )
    parser.add_argument(
        "--report",
        "--report-path",
        dest="report_path",
        type=Path,
        default=None,
        help="Optional path for writing the Markdown report",
    )
    parser.set_defaults(execute=False)
    return parser


def _build_agent(retriever_mode: str) -> RStatsAgent:
    tfidf_retriever = build_default_retriever()
    if retriever_mode == "tfidf":
        return RStatsAgent(retriever=tfidf_retriever)

    index_path = DEFAULT_VECTOR_ARTIFACTS_DIR / "embeddings.npy"
    metadata_path = DEFAULT_VECTOR_ARTIFACTS_DIR / "metadata.jsonl"
    if index_path.exists() and metadata_path.exists():
        vector_index = NumpyVectorIndex.load(index_path=index_path, metadata_path=metadata_path)
        hybrid = HybridRetriever(
            tfidf_retriever=tfidf_retriever,
            embedding_backend=LocalHashEmbeddingBackend(),
            vector_index=vector_index,
        )
    else:
        hybrid = HybridRetriever(tfidf_retriever=tfidf_retriever)
        hybrid.diagnostics.append("vector_artifacts_missing=falling_back_to_tfidf")
    return RStatsAgent(retriever=hybrid)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    agent = _build_agent(args.retriever)
    response = agent.run(
        AgentRequest(
            question=args.question,
            top_k=args.top_k,
            execute=args.execute,
            retriever=args.retriever,
            repair=args.repair,
            max_repairs=args.max_repairs,
            timeout_sec=args.timeout_sec,
            docker_image=args.docker_image,
        )
    )
    if args.report_path:
        report = write_markdown_report(response, args.report_path)
        print(report.markdown)
        print(f"\n[report] {report.path}")
    else:
        print(render_markdown_report(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
