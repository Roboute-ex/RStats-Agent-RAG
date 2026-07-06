# RStats-Agent-RAG

`RStats-Agent-RAG` 是一个面向 R 统计生态的 local-first Agent + RAG 工程 MVP。它不是一个简单的 prompt demo，而是把中文或英文统计分析需求转成可审计的 R 代码，并同时给出解释、输入假设、可能失败原因、引用片段、执行状态和诊断信息。

当前版本为 v0.4。项目覆盖三类高频任务：`dplyr` 数据清洗与分组汇总、`ggplot2` 声明式可视化、`lme4` 线性混合效应模型。v0.4 在 v0.3 的 embedding backend、本地 vector index 和 hybrid retrieval 基础上，新增 optional Docker/R 执行、结构化 R 错误诊断、规则化修复建议和 one-shot repair loop。

项目坚持 local-first 和 offline-test-first：默认不调用在线 LLM，不依赖 OpenAI API，不要求测试联网、下载模型、安装 R、安装 Docker 或安装 FAISS。Docker/R 执行是可选能力，不可用时返回 `skipped`。repair loop 是 deterministic rule-based 规则系统，不会联网安装 R 包，也不会调用 LLM。

## 项目动机

普通 R 代码生成器容易给出“看起来能跑”的代码，但统计分析更在意方法是否适配、函数语义是否正确、输入数据假设是否清晰、包版本和来源是否可追踪，以及失败时能否暴露诊断线索。

R 生态知识分散在 CRAN package pages、reference manuals、vignettes、示例和官方文档中。本项目采用 RAG-first，而不是一开始就接在线 LLM，是为了优先保证知识来源可追踪、解释可审计、测试可复现，并为后续更强的生成模型或执行修复闭环留下清晰接口。

## Agent 如何工作

```mermaid
flowchart LR
  Q["User Query"] --> QR["Query Rewriter"]
  QR --> CL["Corpus Loader"]
  CL --> TF["TF-IDF Retriever"]
  CL --> VE["Vector Retriever"]
  TF --> HF["Hybrid Rank Fusion"]
  VE --> HF
  HF --> CF["Context Fusion"]
  CF --> TG["Template Generator"]
  TG --> SC["Safety Checker"]
  SC --> EX["Optional Docker/R Executor"]
  EX --> DG["Execution Diagnostics"]
  DG --> RP["Rule-based Repair Suggestions"]
  RP --> MD["Markdown Report"]
```

- Query Rewriter：把自然语言需求扩展为包名、函数名和统计术语。
- Corpus Loader：优先加载 `data/processed/corpus.jsonl`，缺失时 fallback 到 fixture corpus。
- TF-IDF Retriever：稳定、离线、可测试的词法检索。
- Vector Retriever：基于 embedding 的本地语义检索。
- Hybrid Rank Fusion：合并 lexical score 和 vector score。
- Context Fusion：按包、来源优先级和任务类型组织引用片段。
- Template Generator：当前使用 deterministic templates，不调用在线 LLM。
- Safety Checker：阻止危险 R 调用。
- Optional Executor：只有 `--execute` 时尝试 Docker/R，不可用时 graceful skipped。
- Diagnostics + Repair：对 stderr/stdout 做结构化分类，并给出规则化修复建议。
- Report：输出 R 代码、解释、假设、失败原因、引用、执行诊断和 repair loop summary。

## 版本演进

| 版本 | 主题 | 核心新增 | 工程意义 |
| --- | --- | --- | --- |
| v0.1 | Local Agent/RAG MVP | fixture corpus、query rewrite、TF-IDF retrieval、template generator、safety、CLI、Markdown report | 跑通本地可测试 Agent 闭环 |
| v0.2 | CRAN Official Corpus + License Ledger | CRAN metadata parser、offline fixtures、processed corpus、license ledger、provenance | 从 handwritten fixture demo 走向可审计知识库 |
| v0.3 | Embedding Backend + Local Vector Index | local hash embedding、optional sentence-transformers、numpy vector index、optional FAISS、hybrid retrieval | 从关键词检索扩展到本地向量检索 RAG 架构 |
| v0.4 | R Execution Diagnostics + Repair Loop | optional Docker/R execution、structured diagnostics、rule-based repair suggestions、one-shot repair loop | 从“生成代码”推进到“执行反馈和修复建议”闭环 |

## 当前支持任务

| 任务类型 | 示例需求 | 生成能力 | 解释能力 |
| --- | --- | --- | --- |
| dplyr 数据清洗与汇总 | 删除 `price` 缺失，按 `store` / `month` 汇总 `revenue` | `filter` / `mutate` / `group_by` / `summarise` / `arrange` | 解释字段要求、NA、分组汇总和收入计算 |
| ggplot2 可视化 | `mpg` 散点图，颜色映射 `class`，按 `drv` 分面 | `ggplot` / `aes` / `geom_point` / `facet_wrap` / `labs` | 解释 aesthetic mapping、图层和分面 |
| lme4 混合效应模型 | `Reaction ~ Days + (Days \| Subject)` | `lmer` / `summary` / `fixef` / `ranef` | 解释固定效应、随机效应、随机截距/斜率和重复测量 |

## v0.4 执行诊断与修复

默认不会执行 R 代码。只有显式传入 `--execute` 时，CLI 才会尝试通过 Docker 运行生成的 R 脚本。Docker 不存在、本地镜像不存在或执行被静态安全检查阻止时，结果会以结构化 `ExecutionResult` 返回，CLI 不会失败。

v0.4 识别的诊断类型包括：

- `missing_package`
- `missing_function`
- `object_not_found`
- `column_not_found`
- `syntax_error`
- `parse_error`
- `lme4_convergence`
- `lme4_singular_fit`
- `package_namespace_error`
- `unknown_error`

repair loop 是规则化、确定性的 one-shot 流程。它可以为缺失 `library(dplyr)` / `library(ggplot2)` / `library(lme4)` 给出补丁，为 lme4 singular fit 给出简化随机效应结构的候选补丁。它不会自动 `install.packages()`，不会联网安装 R 包，也不会盲目修改列名。

Docker 运行参数包含 `--read-only`、`--cpus 1.0`、`--memory 1g`、`--pids-limit 256`、`--network none` 和临时目录 bind mount。这只是可选的受限执行原型，不是生产级安全沙箱。

## 快速开始

```powershell
py -3 -m pip install -e ".[dev]"
py -3 -m pytest -q
```

可选向量依赖：

```powershell
py -3 -m pip install -e ".[dev,vector]"
```

`faiss-cpu` 和 `sentence-transformers` 只在 `vector` optional dependencies 中，不属于核心依赖。

## CLI Demo

默认不执行 R：

```powershell
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，删除 price 缺失或小于等于 0 的行，按 store 和 month 汇总 revenue" --no-execute
```

```powershell
py -3 -m rstats_agent.cli "请用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，颜色映射 class，并按 drv 分面" --no-execute
```

```powershell
py -3 -m rstats_agent.cli "请用 lme4 对 sleepstudy 拟合 Reaction ~ Days + (Days | Subject) 并解释固定效应和随机效应" --no-execute
```

启用 v0.4 optional execution + repair：

```powershell
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，删除 price 缺失并按 store 汇总 revenue" --execute --repair --max-repairs 1
```

如果 Docker/R 不可用，输出会显示 `execution_status=skipped` 和原因，不影响核心流程。

可选 hybrid retrieval：

```powershell
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，按 store 和 month 汇总 revenue" --retriever hybrid --no-execute
```

## Markdown 报告

CLI 输出 Markdown 报告，包含：

- 用户问题
- 检索到的知识片段 ID
- 生成的 R 代码
- 简洁解释
- 输入数据假设
- 可能失败原因与修复建议
- 引用片段
- 执行状态
- 执行诊断
- 修复建议
- Repair Loop Summary
- `knowledge_source` / `retriever` diagnostics

## v0.2 CRAN Corpus 构建

离线 fixture 构建流程：

```powershell
py -3 data/crawl_cran_packages.py --offline-fixtures --output data/raw/cran_packages.json
py -3 data/build_corpus.py --input data/raw/cran_packages.json --output data/processed/corpus.jsonl
py -3 data/build_license_ledger.py --input data/raw/cran_packages.json --output data/processed/licenses.jsonl
```

真实 CRAN metadata 采集只应由开发者手动运行；测试不会访问网络。

## v0.3 Vector Index 构建

默认 local-hash + numpy：

```powershell
py -3 data/build_vector_index.py --backend local-hash --index-backend numpy --output-dir knowledge/artifacts --query "dplyr filter missing price group_by summarise revenue" --top-k 3
```

可选 FAISS：

```powershell
py -3 -m pip install -e ".[dev,vector]"
py -3 data/build_vector_index.py --backend local-hash --index-backend faiss --output-dir knowledge/artifacts --query "lme4 random effects lmer sleepstudy" --top-k 3
```

如果 FAISS 未安装，FAISS 路径会给出清晰错误；默认测试和 numpy 构建不受影响。

## 目录结构

```text
data/
  build_vector_index.py
  crawl_cran_packages.py
  build_corpus.py
  build_license_ledger.py
knowledge/artifacts/
  .gitkeep
rstats_agent/
  embeddings/
  agents/
    repair_loop.py
  execution/
    diagnostics.py
    repair.py
    r_executor.py
    safety.py
  knowledge/
  reporting/
tests/
```

`knowledge/artifacts/` 中生成的索引文件、`data/processed/*.jsonl`、`reports/*.md` 和执行日志都不应提交。

## 测试

```powershell
py -3 -m pytest -q
```

测试覆盖 v0.1/v0.2/v0.3/v0.4 的核心路径，并保持离线 deterministic。默认测试不依赖 Docker/R/FAISS/sentence-transformers。

## 工程亮点

- Local-first Agent/RAG architecture
- Deterministic offline testing
- CRAN metadata corpus builder
- License ledger and provenance-aware corpus schema
- Processed corpus + fixture fallback
- Embedding backend abstraction
- Numpy vector index fallback and optional FAISS
- Hybrid lexical + vector retrieval
- Static R safety guard
- Optional Docker/R execution
- Structured R error diagnostics
- Rule-based repair suggestions and one-shot repair loop
- Clear versioned roadmap

## 当前边界

- 不调用在线 LLM。
- 不依赖 OpenAI API。
- 不做真实大规模 CRAN 爬虫。
- 不解析完整 PDF/vignette 正文。
- 不自动下载 sentence-transformer 模型。
- 不默认要求 FAISS。
- 不自动联网安装 R 包。
- 不替代统计专家审查。
- 当前 generator 是 template-based，不是自由生成模型。
- 当前 Docker/R 执行是受限原型，不是生产级安全沙箱。

## Roadmap

- v0.5：Web UI / FastAPI。
- v0.6：retrieval evaluation，包含 Recall@k / MRR / nDCG。
- v0.7：更多 R 包与更丰富文档解析。
