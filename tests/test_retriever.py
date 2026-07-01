from rstats_agent.knowledge.corpus_loader import load_corpus
from rstats_agent.knowledge.query_rewriter import rewrite_query
from rstats_agent.knowledge.retriever import LocalTfidfRetriever


def _packages_for(question: str) -> set[str]:
    retriever = LocalTfidfRetriever(load_corpus())
    results = retriever.search(rewrite_query(question), top_k=6)
    assert results == sorted(results, key=lambda item: item.score, reverse=True)
    return {item.package for item in results}


def test_retrieves_dplyr_chunks_for_dplyr_question():
    packages = _packages_for("清洗销售数据，删除 price 缺失，按 store 和 month 汇总 revenue")

    assert "dplyr" in packages


def test_retrieves_ggplot2_chunks_for_plot_question():
    packages = _packages_for("用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，颜色映射 class")

    assert "ggplot2" in packages


def test_retrieves_lme4_chunks_for_mixed_model_question():
    packages = _packages_for("用 lme4 sleepstudy 拟合 Reaction ~ Days + (Days | Subject)")

    assert "lme4" in packages
