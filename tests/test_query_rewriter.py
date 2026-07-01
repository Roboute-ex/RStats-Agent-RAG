from rstats_agent.knowledge.query_rewriter import detect_task_types, rewrite_query


def test_rewrites_dplyr_sales_question():
    rewritten = rewrite_query("清洗销售数据，按 store 和 month 汇总 revenue")

    assert detect_task_types("清洗销售数据，按 store 和 month 汇总 revenue") == ["dplyr"]
    assert "dplyr" in rewritten["package_function"]
    assert "group_by" in rewritten["package_function"]
    assert "missing" in rewritten["method_terms"]


def test_rewrites_ggplot2_question():
    rewritten = rewrite_query("请对 mpg 画 displ 和 hwy 的散点图，颜色映射 class，并按 drv 分面")

    assert "ggplot2" in rewritten["package_function"]
    assert "geom_point" in rewritten["package_function"]
    assert "facet" in rewritten["method_terms"]


def test_rewrites_lme4_question():
    rewritten = rewrite_query("用 lme4 对 sleepstudy 拟合混合效应模型并解释固定效应和随机效应")

    assert "lme4" in rewritten["package_function"]
    assert "lmer" in rewritten["package_function"]
    assert "random effects" in rewritten["package_function"]
