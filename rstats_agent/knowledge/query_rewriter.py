"""Deterministic query expansion for the local retrieval stage."""

from __future__ import annotations

from collections.abc import Iterable


DPLYR_KEYWORDS = (
    "清洗",
    "汇总",
    "分组",
    "缺失",
    "销售",
    "revenue",
    "store",
    "month",
    "price",
    "qty",
    "dplyr",
    "filter",
    "mutate",
    "group_by",
    "summarise",
    "summarize",
    "arrange",
)

GGPLOT2_KEYWORDS = (
    "图",
    "散点图",
    "可视化",
    "颜色",
    "分面",
    "mpg",
    "displ",
    "hwy",
    "drv",
    "class",
    "ggplot2",
    "ggplot",
    "aes",
    "geom_point",
    "facet_wrap",
)

LME4_KEYWORDS = (
    "混合效应",
    "随机截距",
    "随机斜率",
    "固定效应",
    "随机效应",
    "random effects",
    "fixed effects",
    "sleepstudy",
    "reaction",
    "days",
    "subject",
    "lme4",
    "lmer",
    "reml",
)


def _contains_any(question: str, keywords: Iterable[str]) -> bool:
    lowered = question.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def detect_task_types(question: str) -> list[str]:
    """Return deterministic task labels in a stable order."""

    labels: list[str] = []
    if _contains_any(question, DPLYR_KEYWORDS):
        labels.append("dplyr")
    if _contains_any(question, GGPLOT2_KEYWORDS):
        labels.append("ggplot2")
    if _contains_any(question, LME4_KEYWORDS):
        labels.append("lme4")
    return labels or ["general_r"]


def rewrite_query(question: str) -> dict[str, str]:
    """Expand a user question into three retrieval-oriented query strings."""

    task_types = detect_task_types(question)
    package_terms = [question]
    method_terms = [question]
    debug_terms = [question, "R error debug diagnostics common mistakes"]

    if "dplyr" in task_types:
        package_terms.append("dplyr filter mutate group_by summarise summarize arrange")
        method_terms.append("data cleaning missing values grouped summary revenue store month price qty")
        debug_terms.append("dplyr missing columns NA non numeric price qty grouped summarise .groups")

    if "ggplot2" in task_types:
        package_terms.append("ggplot2 ggplot aes geom_point facet_wrap labs")
        method_terms.append("scatter plot visualization color mapping facets mpg displ hwy class drv")
        debug_terms.append("ggplot2 missing aesthetics unknown columns facet variable discrete color")

    if "lme4" in task_types:
        package_terms.append("lme4 lmer formula REML random effects fixed effects sleepstudy")
        method_terms.append("linear mixed effects model random intercept random slope Subject Days Reaction")
        debug_terms.append("lme4 convergence singular fit grouping factor formula syntax REML")

    if task_types == ["general_r"]:
        package_terms.append("R statistics tidyverse ggplot2 lme4")
        method_terms.append("data analysis visualization statistical model")
        debug_terms.append("missing package missing column invalid formula")

    return {
        "package_function": " ".join(package_terms),
        "method_terms": " ".join(method_terms),
        "error_debug": " ".join(debug_terms),
    }
