from rstats_agent.agents.r_agent import RStatsAgent


def test_agent_pipeline_dplyr():
    response = RStatsAgent().run("请用 dplyr 清洗销售数据，按 store 和 month 汇总 revenue")

    assert response.task_type == "dplyr"
    assert "sales_clean" in response.r_code
    assert response.execution.status == "skipped"
    assert any(citation.startswith("dplyr-") for citation in response.citations)


def test_agent_pipeline_ggplot2():
    response = RStatsAgent().run("请用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，按 drv 分面")

    assert response.task_type == "ggplot2"
    assert "geom_point" in response.r_code
    assert any(citation.startswith("ggplot2-") for citation in response.citations)


def test_agent_pipeline_lme4():
    response = RStatsAgent().run("请用 lme4 对 sleepstudy 拟合 Reaction ~ Days + (Days | Subject)")

    assert response.task_type == "lme4"
    assert "lmer(" in response.r_code
    assert any(citation.startswith("lme4-") for citation in response.citations)
