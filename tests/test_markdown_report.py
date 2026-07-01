from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.reporting.markdown import render_markdown_report


def test_markdown_report_contains_required_sections():
    response = RStatsAgent().run("请用 ggplot2 对 mpg 画散点图")
    markdown = render_markdown_report(response)

    assert "## 用户问题" in markdown
    assert "## 检索到的知识片段 ID" in markdown
    assert "## 生成的 R 代码" in markdown
    assert "```r" in markdown
    assert "## 简洁解释" in markdown
    assert "## 输入数据假设" in markdown
    assert "## 可能失败原因与修复建议" in markdown
    assert "## 执行状态" in markdown
