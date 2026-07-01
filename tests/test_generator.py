from rstats_agent.agents.generator import generate_answer
from rstats_agent.knowledge.corpus_loader import load_corpus
from rstats_agent.knowledge.query_rewriter import rewrite_query
from rstats_agent.knowledge.retriever import LocalTfidfRetriever


def _context(question: str):
    retriever = LocalTfidfRetriever(load_corpus())
    return retriever.search(rewrite_query(question), top_k=6)


def test_generates_dplyr_template():
    answer = generate_answer("请用 dplyr 清洗销售数据并汇总 revenue", _context("dplyr revenue"))

    assert answer.task_type == "dplyr"
    assert "library(dplyr)" in answer.r_code
    assert "summarise(" in answer.r_code
    assert "arrange(desc(total_revenue))" in answer.r_code


def test_generates_ggplot2_template():
    answer = generate_answer("请用 ggplot2 画 mpg 散点图", _context("ggplot2 mpg scatter"))

    assert answer.task_type == "ggplot2"
    assert "library(ggplot2)" in answer.r_code
    assert "geom_point" in answer.r_code
    assert "facet_wrap(~ drv)" in answer.r_code


def test_generates_lme4_template():
    answer = generate_answer("请用 lme4 对 sleepstudy 拟合混合效应模型", _context("lme4 sleepstudy"))

    assert answer.task_type == "lme4"
    assert "library(lme4)" in answer.r_code
    assert "Reaction ~ Days + (Days | Subject)" in answer.r_code
    assert "fixef(model)" in answer.r_code
