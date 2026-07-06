"""Markdown report renderer for Agent responses."""

from __future__ import annotations

from pathlib import Path

from rstats_agent.schemas import AgentResponse, ReportResult


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- 无"
    return "\n".join(f"- {item}" for item in items)


def _truncate(text: str, limit: int = 500) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _diagnostics_section(response: AgentResponse) -> list[str]:
    lines = ["## 执行诊断"]
    if response.execution.status == "skipped" and not response.execution_diagnostics:
        lines.append("- 未启用执行，或 Docker/R 不可用；无错误诊断。")
        return lines
    if not response.execution_diagnostics:
        lines.append("- 无错误诊断。")
        return lines

    for diagnostic in response.execution_diagnostics:
        lines.extend(
            [
                f"- error_type: {diagnostic.error_type}",
                f"  severity: {diagnostic.severity}",
                f"  likely_cause: {diagnostic.likely_cause}",
                f"  suggested_fix: {diagnostic.suggested_fix}",
                f"  evidence: {_truncate(diagnostic.evidence, 220) or '无'}",
            ]
        )
    return lines


def _repair_section(response: AgentResponse) -> list[str]:
    lines = ["## 修复建议"]
    if not response.repair_suggestions:
        lines.append("- 无修复建议；通常是未启用 --repair，或没有执行错误诊断。")
        return lines

    for suggestion in response.repair_suggestions:
        lines.extend(
            [
                f"- repair_type: {suggestion.repair_type}",
                f"  confidence: {suggestion.confidence}",
                f"  applied: {suggestion.applied}",
                f"  message: {suggestion.message}",
            ]
        )
        if suggestion.patched_code:
            lines.extend(["", "```r", suggestion.patched_code.rstrip(), "```"])
    return lines


def _repair_loop_section(response: AgentResponse) -> list[str]:
    loop = response.repair_loop
    if loop is None:
        return [
            "## Repair Loop Summary",
            "- attempts: 0",
            f"- original status: {response.execution.status}",
            "- repaired status: not_attempted",
            "- repaired code executed: false",
        ]

    repaired_status = loop.repaired_execution.status if loop.repaired_execution else "not_attempted"
    repaired_executed = bool(loop.repaired_execution and loop.repaired_execution.status != "skipped")
    return [
        "## Repair Loop Summary",
        f"- attempts: {loop.attempts}",
        f"- original status: {loop.original_execution.status}",
        f"- repaired status: {repaired_status}",
        f"- repaired code executed: {str(repaired_executed).lower()}",
    ]


def render_markdown_report(response: AgentResponse) -> str:
    chunk_ids = [item.chunk_id for item in response.context]
    diagnostics = response.diagnostics + [
        f"retrieved={len(response.retrieved)}",
        f"execution_status={response.execution.status}",
    ]

    sections = [
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
        f"- ok: {response.execution.ok}",
        f"- skipped: {response.execution.skipped}",
        f"- returncode: {response.execution.returncode}",
        f"- reason: {response.execution.reason or '无'}",
        f"- stdout: {_truncate(response.execution.stdout, 500) or '无'}",
        f"- stderr: {_truncate(response.execution.stderr, 500) or '无'}",
        "",
        *_diagnostics_section(response),
        "",
        *_repair_section(response),
        "",
        *_repair_loop_section(response),
        "",
        "## 诊断信息",
        _bullet_list(diagnostics),
        "",
    ]
    return "\n".join(sections)


def write_markdown_report(response: AgentResponse, path: str | Path) -> ReportResult:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown_report(response)
    report_path.write_text(markdown, encoding="utf-8")
    return ReportResult(markdown=markdown, path=report_path, diagnostics=[f"报告已写入 {report_path}"])
