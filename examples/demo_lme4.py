from rstats_agent.agents.r_agent import RStatsAgent
from rstats_agent.reporting.markdown import render_markdown_report


QUESTION = "请用 lme4 对 sleepstudy 拟合 Reaction ~ Days + (Days | Subject) 并解释固定效应和随机效应"


if __name__ == "__main__":
    print(render_markdown_report(RStatsAgent().run(QUESTION)))
