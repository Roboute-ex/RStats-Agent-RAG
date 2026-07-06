# Changelog

## 0.5.0

- Added optional Streamlit interactive demo with built-in demo cases, retriever selection, optional execute/repair controls, result display, and Markdown report download.
- Added optional FastAPI service with `/health`, `/demo-cases`, and `/analyze` endpoints.
- Added `app/demo_cases.py` for reusable local demo scenarios across UI, API, and tests.
- Added `docs/demo_script.md` for interview/demo walkthroughs covering v0.1-v0.5, local-first testing, optional execution, and repair loop boundaries.
- Added `web` optional dependencies for `streamlit`, `fastapi`, and `uvicorn`; core dependencies remain lightweight.
- Preserved CLI and local-first workflow; default tests remain offline and deterministic without browser, real server, Docker/R, FAISS, sentence-transformers, network, or API keys.

## 0.4.0

- 扩展 `ExecutionResult`，新增 `ok`、`skipped`、`reason`、`timed_out`、`duration_sec` 和 `command_preview` 等结构化字段。
- 新增 `ExecutionDiagnostic`、`RepairSuggestion` 和 `RepairLoopResult` dataclass。
- 增强 Docker/R executor：使用临时 `task.R`、`Rscript`、`--read-only`、`--cpus 1.0`、`--memory 1g`、`--pids-limit 256`、`--network none` 和 bind mount。
- 新增 `execution/diagnostics.py`，支持 missing package/function、object/column not found、syntax/parse、lme4 convergence/singular fit、namespace 和 unknown error 分类。
- 新增 `execution/repair.py`，提供 deterministic rule-based repair suggestions，不自动联网安装 R 包。
- 新增 `agents/repair_loop.py`，支持 one-shot repair loop 和 repaired code safety check。
- CLI 新增 `--repair`、`--max-repairs`、`--timeout-sec`、`--docker-image`，并保留 `--execute`、`--no-execute`、`--retriever`、`--report/--report-path`。
- Markdown report 新增“执行诊断”“修复建议”和“Repair Loop Summary”章节。
- README/AGENTS 更新到 v0.4，明确 Docker/R 执行和 repair loop 都是 optional、deterministic、非 LLM、非生产级沙箱。
- 新增 v0.4 离线测试，覆盖 diagnostics、repair rules、executor、repair loop、CLI 和 Markdown report。

## 0.3.0

- 新增 embedding backend 协议。
- 新增 deterministic `LocalHashEmbeddingBackend`，用于离线测试和默认 fallback。
- 新增 optional `SentenceTransformerEmbeddingBackend`，通过 `.[vector]` 安装。
- 新增 `NumpyVectorIndex` 和 optional `FaissVectorIndex`。
- 新增 `data/build_vector_index.py`，支持从 processed corpus 或 fixture corpus 构建本地向量 artifacts。
- 新增 `HybridRetriever`，支持 TF-IDF 与向量检索分数融合，并在缺少向量索引时 fallback 到 TF-IDF。
- CLI 新增 `--retriever tfidf|hybrid`，默认仍为 `tfidf`。
- 更新 `.gitignore`，忽略 `knowledge/artifacts` 生成索引文件。
- 新增 v0.3 离线测试，覆盖 embedding backend、vector index、hybrid retrieval 和 vector build 脚本。
- 增强 README 展示内容，补充项目动机、Agent 架构、版本演进、RAG 知识库设计、v0.3 向量检索设计、工程亮点和面试讲法。

## 0.2.0

- 新增 `data/` 层，用于 CRAN package page metadata 采集、raw 保存、processed corpus 构建和 license ledger 构建。
- 添加 dplyr、ggplot2、lme4、renv 的离线 CRAN HTML fixtures。
- 添加 CRAN parser、corpus builder、license ledger builder 的 deterministic 离线测试。
- 升级 corpus loader：默认优先加载 `data/processed/corpus.jsonl`，不存在时回退 v0.1 fixture corpus。
- 更新 README/AGENTS，明确 v0.2 只采集 metadata，不解析完整 PDF/vignette 正文，不下载源码 tarball。

## 0.1.0

- 初始化 `RStats-Agent-RAG` 本地 MVP。
- 添加 R 统计生态 fixture 知识片段，覆盖 dplyr、ggplot2、lme4。
- 实现 deterministic query rewriting。
- 实现基于 `TfidfVectorizer` 的本地 retriever 和 metadata 加权。
- 实现上下文融合、三类模板生成、静态 R 安全检查和可选 Docker R executor。
- 实现 CLI demo、Markdown 报告、examples 和 deterministic 测试。
