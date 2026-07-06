from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.reporting.markdown import render_markdown_report
from rstats_agent.schemas import AgentResponse, ExecutionDiagnostic, ExecutionResult, RepairSuggestion


def test_markdown_report_contains_required_sections():
    response = RStatsAgent().run("use ggplot2 to draw a scatter plot")
    markdown = render_markdown_report(response)

    assert "# RStats-Agent-RAG Analysis Report" in markdown
    assert "RStats-Agent-RAG v0.1" not in markdown
    assert "v0.1 使用" not in markdown
    assert "knowledge_source=" in markdown
    assert "## 用户问题" in markdown
    assert "## 检索到的知识片段 ID" in markdown
    assert "## 生成的 R 代码" in markdown
    assert "```r" in markdown
    assert "## 简洁解释" in markdown
    assert "## 输入数据假设" in markdown
    assert "## 可能失败原因与修复建议" in markdown
    assert "## 执行状态" in markdown
    assert "## 执行诊断" in markdown
    assert "未启用执行" in markdown
    assert "## 修复建议" in markdown
    assert "## Repair Loop Summary" in markdown


def test_markdown_report_renders_diagnostics_and_repair_suggestions():
    response = AgentResponse(
        question="demo",
        task_type="dplyr",
        rewritten_queries={},
        retrieved=[],
        context=[],
        r_code="sales %>% filter(price > 0)",
        explanation="demo",
        assumptions=[],
        failure_modes=[],
        citations=[],
        execution=ExecutionResult(status="failed", stderr="Error in filter(): could not find function"),
        diagnostics=[],
        execution_diagnostics=[
            ExecutionDiagnostic(
                error_type="missing_function",
                severity="error",
                message="missing function",
                evidence="could not find function",
                likely_cause="library(dplyr) is missing",
                suggested_fix="Add library(dplyr).",
            )
        ],
        repair_suggestions=[
            RepairSuggestion(
                repair_type="add_library_dplyr",
                message="Add library(dplyr).",
                patched_code="library(dplyr)\n\nsales %>% filter(price > 0)",
                confidence="high",
                applied=True,
            )
        ],
    )

    markdown = render_markdown_report(response)

    assert "error_type: missing_function" in markdown
    assert "likely_cause: library(dplyr) is missing" in markdown
    assert "repair_type: add_library_dplyr" in markdown
    assert "confidence: high" in markdown
    assert "library(dplyr)" in markdown
