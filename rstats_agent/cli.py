"""Command line demo entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.schemas import AgentRequest
from rstats_agent.reporting.markdown import render_markdown_report, write_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RStats-Agent-RAG local v0.1 demo")
    parser.add_argument("question", help="中文或英文 R 统计任务需求")
    parser.add_argument("--top-k", type=int, default=6, help="检索知识片段数量，默认 6")
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    agent = RStatsAgent()
    response = agent.run(AgentRequest(question=args.question, top_k=args.top_k, execute=args.execute))
    if args.report_path:
        report = write_markdown_report(response, args.report_path)
        print(report.markdown)
        print(f"\n[report] {report.path}")
    else:
        print(render_markdown_report(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
