# RStats-Agent-RAG

面向 R 统计生态的 Agent 与 RAG 工程 MVP。v0.1 聚焦一个可运行、可测试、可演示的本地闭环：用户用中文或英文描述 R 统计任务，系统用本地知识库检索相关片段，再用 deterministic 模板生成 R 代码、解释、引用、诊断和 Markdown 报告。

## v0.1 覆盖范围

- dplyr 数据清洗与汇总：`filter`、`mutate`、`group_by`、`summarise`、`arrange`
- ggplot2 可视化代码生成：`ggplot`、`aes`、`geom_point`、`facet_wrap`、`labs`
- lme4 混合效应模型代码生成与解释：`lmer`、固定效应、随机效应、公式语法、`sleepstudy`

v0.1 默认不调用 OpenAI API，不依赖外网 embedding，不依赖 Milvus/Weaviate，也不要求本机安装 R 或 Docker 才能通过核心测试。R 执行是 optional capability：默认只做静态安全检查并返回 `skipped`。

## 快速开始

```powershell
py -3 -m pip install -e ".[dev]"
py -3 -m pytest
```

如果你的环境中 `python` 指向可用解释器，也可以把 `py -3` 替换为 `python`。

## CLI 演示

```powershell
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，删除 price 缺失或小于等于 0 的行，按 store 和 month 汇总 revenue" --no-execute
```

```powershell
py -3 -m rstats_agent.cli "请用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，颜色映射 class，并按 drv 分面" --no-execute
```

```powershell
py -3 -m rstats_agent.cli "请用 lme4 对 sleepstudy 拟合 Reaction ~ Days + (Days | Subject) 并解释固定效应和随机效应" --no-execute
```

写出 Markdown 报告：

```powershell
py -3 -m rstats_agent.cli "请用 ggplot2 对 mpg 画散点图" --report-path reports/demo_ggplot2.md
```

尝试 Docker 执行 R 代码：

```powershell
py -3 -m rstats_agent.cli "请用 lme4 对 sleepstudy 拟合 Reaction ~ Days + (Days | Subject)" --execute
```

如果 Docker 不可用，或本地没有 `rocker/r-ver:4.3.3` 镜像，执行状态会返回 `skipped`，不会影响核心流程。

## 目录结构

```text
rstats_agent/
  agents/          # Agent 编排、上下文融合、模板生成
  execution/       # R 代码安全检查与可选 Docker 执行
  knowledge/       # JSONL 语料加载、query rewrite、TF-IDF 检索
  reporting/       # Markdown 报告渲染
examples/          # 三个本地 demo
reports/           # 报告输出目录
tests/             # deterministic 单元测试与流水线测试
```

核心语料位于 `rstats_agent/knowledge/fixtures/r_core_corpus.jsonl`，包含 14 条官方风格 fixture 片段。

## 流水线

1. Query rewriting：将用户问题扩展为 `package_function`、`method_terms`、`error_debug` 三组检索词。
2. Retriever：使用 `sklearn.feature_extraction.text.TfidfVectorizer` 做本地 TF-IDF 检索，并对命中包名/函数名的片段做轻量 metadata 加权。
3. Context fusion：按 `P0/P1/P2`、来源类型和 score 排序上下文。
4. Generator：基于三类任务模板 deterministic 生成 R 代码和解释。
5. Safety checker：静态检测 `system()`、`unlink()`、`download.file()`、`install.packages()` 等危险调用。
6. Optional executor：默认跳过执行；`--no-execute` 可显式保持不执行；启用 `--execute` 后，只有 Docker 与本地镜像可用时才执行。
7. Reporter：输出 Markdown 报告，包含问题、片段 ID、代码、解释、假设、失败原因、执行状态和诊断。

## 测试

```powershell
py -3 -m pytest
```

测试不依赖外网、API key、真实 CRAN 下载、本机 R 或 Docker 环境。当前覆盖：

- corpus loader
- query rewriter
- TF-IDF retriever
- template generator
- safety checker
- optional R executor fallback
- Agent end-to-end pipeline
- Markdown report renderer

## v0.1 能力边界

- 不是生产级 R 代码生成器，当前只覆盖 dplyr、ggplot2、lme4 的小型模板。
- 不做真实大规模爬虫，不做在线 embedding，不调用在线 LLM。
- 不自动安装 R 包，不自动下载 Docker 镜像。
- 检索语料是 fixture，不代表完整官方文档。
- 安全检查是静态规则，可阻止常见危险调用，但不是完整沙箱。

## Roadmap

- v0.2：扩展知识库 schema，引入更丰富的 tidyverse/modeling 片段。
- v0.3：加入可替换 embedding backend，并保持本地 fallback。
- v0.4：支持更细粒度的错误诊断和 R 代码修复建议。
- v0.5：提供可选 Web UI 与交互式报告。
- v1.0：在明确配置下接入真实 LLM、文档同步和更强执行隔离。
