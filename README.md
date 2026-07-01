# RStats-Agent-RAG

面向 R 统计生态的 Agent 与 RAG 工程 MVP。当前版本为 v0.2，在 v0.1 本地 Agent/RAG 流程之上，新增可审计、可测试、可离线回归的 CRAN 官方 package metadata 采集与语料构建层。

## 当前能力

v0.1 核心能力保持不变：

- dplyr 数据清洗与汇总代码生成
- ggplot2 可视化代码生成
- lme4 混合效应模型代码生成与解释
- 本地 fixture fallback、deterministic query rewriting、TF-IDF 检索、模板生成、安全检查、可选执行 fallback、Markdown 报告和 CLI

v0.2 新增能力：

- `data/` 层：CRAN package page metadata 采集、raw JSON 保存、processed corpus 构建、license ledger 构建
- 目标包限定为 `dplyr`、`ggplot2`、`lme4`、`renv`
- 支持 offline fixtures 构建流程，测试不访问网络
- `corpus_loader` 优先加载 `data/processed/corpus.jsonl`；不存在时回退到 v0.1 fixture 语料

v0.2 只采集 CRAN package page metadata，不解析完整 PDF 正文，不下载源码 tarball，不解析完整 vignette 内容。

## 快速开始

```powershell
py -3 -m pip install -e ".[dev]"
py -3 -m pytest -q
```

## v0.1 CLI Demo

默认不执行 R 代码；`--no-execute` 是兼容参数，可显式保持不执行。

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

如果 Docker 不可用，或本地没有 `rocker/r-ver:4.3.3` 镜像，执行状态会返回 `skipped`，不影响核心流程。

## v0.2 CRAN Corpus 构建

离线 fixture 构建流程：

```powershell
py -3 data/crawl_cran_packages.py --offline-fixtures --output data/raw/cran_packages.json
py -3 data/build_corpus.py --input data/raw/cran_packages.json --output data/processed/corpus.jsonl
py -3 data/build_license_ledger.py --input data/raw/cran_packages.json --output data/processed/licenses.jsonl
```

手动真实 CRAN metadata 采集：

```powershell
py -3 data/crawl_cran_packages.py --packages dplyr ggplot2 lme4 renv --output data/raw/cran_packages.json
```

真实联网抓取只应由开发者手动运行；测试不会访问网络。

## 目录结构

```text
data/
  crawl_cran_packages.py       # CRAN package page metadata parser/crawler
  build_corpus.py              # raw package metadata -> processed corpus JSONL
  build_license_ledger.py      # raw package metadata -> license ledger JSONL
  raw/fixtures/                # offline CRAN HTML fixtures
  processed/                   # generated corpus/license outputs
rstats_agent/
  agents/                      # Agent 编排、上下文融合、模板生成
  execution/                   # R 代码安全检查与可选 Docker 执行
  knowledge/                   # JSONL 语料加载、query rewrite、TF-IDF 检索
  reporting/                   # Markdown 报告渲染
tests/                         # deterministic 离线测试
```

生成文件 `data/raw/cran_packages.json`、`data/processed/*.jsonl` 默认被 `.gitignore` 忽略。

## 测试

```powershell
py -3 -m pytest -q
```

测试不依赖外网、API key、CRAN 下载、本机 R 或 Docker。覆盖范围包括：

- v0.1 corpus loader、query rewriter、retriever、generator、safety、executor fallback、Agent pipeline、Markdown report、CLI
- v0.2 CRAN HTML parser、offline crawl、processed corpus builder、license ledger builder、processed corpus 优先加载和 fixture fallback

## 能力边界

- 不调用 OpenAI API 或在线 LLM。
- 不引入 BGE、FAISS、Milvus、Weaviate。
- 不做真实大规模 CRAN 爬虫。
- v0.2 只解析 package page metadata，不解析完整 manual PDF/vignette 正文，不下载源码 tarball。
- 安全检查是静态规则，不是完整沙箱。

## Roadmap

- v0.3：embedding backend + FAISS local index，并保留本地 deterministic fallback。
- v0.4：R execution + repair loop，增强错误诊断与修复建议。
- v0.5：Web UI / FastAPI，提供更完整的交互式演示。
