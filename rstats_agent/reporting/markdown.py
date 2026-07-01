"""Markdown report renderer for Agent responses."""

from __future__ import annotations

from pathlib import Path

from rstats_agent.schemas import AgentResponse, ReportResult


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- 无"
    return "\n".join(f"- {item}" for item in items)


def render_markdown_report(response: AgentResponse) -> str:
    chunk_ids = [item.chunk_id for item in response.context]
    diagnostics = response.diagnostics + [
        f"retrieved={len(response.retrieved)}",
        f"execution_status={response.execution.status}",
    ]

    return "\n".join(
        [
            "# RStats-Agent-RAG Analysis Report",
            "",
            "## 用户问题",
            response.question,
            "",
            "## 检索到的知识片段 ID",
            _bullet_list(chunk_ids),
            "",
            "## 生成的 R 代码",
            "```r",
            response.r_code.rstrip(),
            "```",
            "",
            "## 简洁解释",
            response.explanation,
            "",
            "## 输入数据假设",
            _bullet_list(response.assumptions),
            "",
            "## 可能失败原因与修复建议",
            _bullet_list(response.failure_modes),
            "",
            "## 引用片段",
            _bullet_list(response.citations),
            "",
            "## 执行状态",
            f"- status: {response.execution.status}",
            f"- returncode: {response.execution.returncode}",
            f"- stdout: {response.execution.stdout.strip() or '无'}",
            f"- stderr: {response.execution.stderr.strip() or '无'}",
            "",
            "## 诊断信息",
            _bullet_list(diagnostics),
            "",
        ]
    )


def write_markdown_report(response: AgentResponse, path: str | Path) -> ReportResult:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown_report(response)
    report_path.write_text(markdown, encoding="utf-8")
    return ReportResult(markdown=markdown, path=report_path, diagnostics=[f"报告已写入 {report_path}"])
