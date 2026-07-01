from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.reporting.markdown import render_markdown_report


QUESTION = "请用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，颜色映射 class，并按 drv 分面"


if __name__ == "__main__":
    print(render_markdown_report(RStatsAgent().run(QUESTION)))
