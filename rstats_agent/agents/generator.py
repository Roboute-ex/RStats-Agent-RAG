"""Deterministic template-based R code generator for v0.1."""

from __future__ import annotations

from dataclasses import dataclass

from rstats_agent.knowledge.query_rewriter import detect_task_types
from rstats_agent.schemas import RetrievalResult


@dataclass(frozen=True)
class GeneratedAnswer:
    task_type: str
    r_code: str
    explanation: str
    assumptions: list[str]
    failure_modes: list[str]


DPLYR_CODE = """library(dplyr)

sales_clean <- sales %>%
  filter(!is.na(price), price > 0, !is.na(qty), qty >= 0) %>%
  mutate(revenue = price * qty) %>%
  group_by(store, month) %>%
  summarise(
    total_revenue = sum(revenue, na.rm = TRUE),
    n_orders = n(),
    .groups = "drop"
  ) %>%
  arrange(desc(total_revenue))

print(sales_clean)
"""

GGPLOT2_CODE = """library(ggplot2)

plot <- ggplot(mpg, aes(x = displ, y = hwy, color = class)) +
  geom_point(alpha = 0.75) +
  facet_wrap(~ drv) +
  labs(
    title = "Highway mileage by engine displacement",
    x = "Engine displacement",
    y = "Highway miles per gallon",
    color = "Class"
  )

print(plot)
"""

LME4_CODE = """library(lme4)

data("sleepstudy", package = "lme4")

model <- lmer(
  Reaction ~ Days + (Days | Subject),
  data = sleepstudy,
  REML = TRUE
)

summary(model)
fixef(model)
ranef(model)
"""

GENERAL_CODE = """# v0.1 could not classify the request as dplyr, ggplot2, or lme4.
# Please mention one of those packages or a supported task pattern.
"""


def _task_from_context(question: str, context: list[RetrievalResult]) -> str:
    detected = detect_task_types(question)
    if detected and detected[0] != "general_r":
        return detected[0]

    package_counts: dict[str, int] = {}
    for item in context:
        package_counts[item.package] = package_counts.get(item.package, 0) + 1
    if not package_counts:
        return "general_r"
    return max(package_counts.items(), key=lambda item: item[1])[0]


def generate_answer(question: str, context: list[RetrievalResult]) -> GeneratedAnswer:
    """Generate deterministic R code and explanation for the supported task family."""

    task_type = _task_from_context(question, context)
    if task_type == "dplyr":
        return GeneratedAnswer(
            task_type="dplyr",
            r_code=DPLYR_CODE,
            explanation=(
                "这段代码先用 filter 删除 price 缺失、price <= 0、qty 缺失或 qty < 0 的记录，"
                "再用 mutate 计算 revenue。随后按 store 和 month 分组，用 summarise 计算总收入和订单数，"
                "最后按 total_revenue 降序排列。"
            ),
            assumptions=[
                "输入对象名为 sales。",
                "sales 至少包含 price、qty、store、month 四列。",
                "price 和 qty 是可参与数值运算的列。",
            ],
            failure_modes=[
                "如果列名不存在，请将模板中的列名改成真实字段名。",
                "如果 price 或 qty 是字符型，需要先转换为 numeric。",
                "如果 revenue 已存在且含义不同，请调整 mutate 中的新列名。",
            ],
        )

    if task_type == "ggplot2":
        return GeneratedAnswer(
            task_type="ggplot2",
            r_code=GGPLOT2_CODE,
            explanation=(
                "这段代码使用 ggplot 初始化 mpg 数据集，将 displ 映射到 x 轴、hwy 映射到 y 轴，"
                "并把 class 映射到颜色。geom_point 绘制散点图，facet_wrap(~ drv) 按驱动类型分面，"
                "labs 提供可读标签。"
            ),
            assumptions=[
                "ggplot2 可访问内置 mpg 数据集。",
                "mpg 包含 displ、hwy、class、drv 四列。",
                "class 和 drv 是适合作为颜色和分面的分类变量。",
            ],
            failure_modes=[
                "如果 mpg 对象被覆盖，请显式使用 ggplot2::mpg 或重新加载 ggplot2。",
                "如果列名不同，请同步修改 aes 和 facet_wrap。",
                "如果分面过多，图形可能拥挤，可先筛选类别或调整布局。",
            ],
        )

    if task_type == "lme4":
        return GeneratedAnswer(
            task_type="lme4",
            r_code=LME4_CODE,
            explanation=(
                "模型 Reaction ~ Days + (Days | Subject) 估计 Days 对 Reaction 的总体平均影响，"
                "同时允许每个 Subject 拥有自己的截距和 Days 斜率。固定效应描述总体趋势，"
                "随机效应描述受试者层面的偏离。"
            ),
            assumptions=[
                "lme4 包可用，并可加载 sleepstudy 示例数据。",
                "Reaction 和 Days 是数值变量，Subject 是分组因子。",
                "每个 Subject 有足够重复观测来估计随机斜率。",
            ],
            failure_modes=[
                "如果出现 singular fit，可尝试简化为 (1 | Subject)。",
                "如果模型不收敛，可检查异常值、缩放连续变量或调整优化器。",
                "如果 lme4 未安装，需要先安装包或改用只生成代码不执行的模式。",
            ],
        )

    return GeneratedAnswer(
        task_type="general_r",
        r_code=GENERAL_CODE,
        explanation="v0.1 只能稳定覆盖 dplyr、ggplot2、lme4 三类本地模板任务。",
        assumptions=["用户问题应明确落在当前支持的三类任务之一。"],
        failure_modes=["请补充 dplyr 清洗汇总、ggplot2 可视化或 lme4 混合效应模型相关关键词。"],
    )
