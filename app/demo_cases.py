"""Built-in demo cases for the optional web UI and API."""

from __future__ import annotations


_DEMO_CASES: tuple[dict[str, str], ...] = (
    {
        "id": "dplyr-clean-summary",
        "title": "dplyr 数据清洗与汇总",
        "category": "dplyr",
        "query": "请用 dplyr 清洗销售数据，删除 price 缺失或小于等于 0 的行，按 store 和 month 汇总 revenue",
    },
    {
        "id": "ggplot2-scatter-facet",
        "title": "ggplot2 可视化",
        "category": "ggplot2",
        "query": "请用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，颜色映射 class，并按 drv 分面",
    },
    {
        "id": "lme4-sleepstudy",
        "title": "lme4 混合效应模型",
        "category": "lme4",
        "query": "请用 lme4 对 sleepstudy 拟合 Reaction ~ Days + (Days | Subject) 并解释固定效应和随机效应",
    },
    {
        "id": "repair-loop-dplyr",
        "title": "repair loop 示例",
        "category": "repair",
        "query": "请用 dplyr 清洗销售数据，删除 price 缺失并按 store 汇总 revenue",
    },
)


def list_demo_cases() -> list[dict[str, str]]:
    """Return copies of the built-in demo cases."""

    return [dict(case) for case in _DEMO_CASES]


def get_demo_case(case_id: str) -> dict[str, str]:
    """Return one demo case by id."""

    for case in _DEMO_CASES:
        if case["id"] == case_id:
            return dict(case)
    known_ids = ", ".join(case["id"] for case in _DEMO_CASES)
    raise ValueError(f"Unknown demo case id: {case_id}. Known ids: {known_ids}")

