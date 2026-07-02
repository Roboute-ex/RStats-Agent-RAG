"""Command line demo entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.config import DEFAULT_VECTOR_ARTIFACTS_DIR
from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.knowledge.hybrid_retriever import HybridRetriever
from rstats_agent.knowledge.retriever import build_default_retriever
from rstats_agent.knowledge.vector_index import NumpyVectorIndex
from rstats_agent.schemas import AgentRequest
from rstats_agent.reporting.markdown import render_markdown_report, write_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RStats-Agent-RAG local demo")
    parser.add_argument("question", help="中文或英文 R 统计任务需求")
    parser.add_argument("--top-k", type=int, default=6, help="检索知识片段数量，默认 6")
    parser.add_argument(
        "--retriever",
        choices=["tfidf", "hybrid"],
        default="tfidf",
        help="检索模式，默认 tfidf；hybrid 在本地向量 artifacts 存在时融合向量检索",
    )
    parser.add_argument("--execute", action="store_true", help="尝试使用本地 Docker 执行生成的 R 代码")
    parser.add_argument(
        "--no-execute",
        dest="execute",
        action="store_false",
        help="兼容参数：显式保持不执行 R 代码",
    )
    parser.add_argument(
        "--report",
        "--report-path",
        dest="report_path",
        type=Path,
        default=None,
        help="可选：将 Markdown 报告写入指定路径",
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
