from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.reporting.markdown import render_markdown_report


QUESTION = "请用 dplyr 清洗销售数据，删除 price 缺失或小于等于 0 的行，按 store 和 month 汇总 revenue"


if __name__ == "__main__":
    print(render_markdown_report(RStatsAgent().run(QUESTION)))
