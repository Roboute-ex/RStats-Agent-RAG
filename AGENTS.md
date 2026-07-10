# AGENTS.md

本项目是 `RStats-Agent-RAG`，当前版本为 v0.6。本仓库优先保持本地、可审计、可测试、Windows PowerShell 友好。

## 工作原则

- 测试必须 deterministic，不能访问网络，不能依赖 API key、真实 CRAN 下载、本机 R、Docker、FAISS 或 sentence-transformers。
- 默认不调用在线 LLM；不要引入 OpenAI、BGE、Milvus、Weaviate 等非当前版本功能。Streamlit/FastAPI 仅允许作为 optional web dependencies。
- README 和公开文档必须真实反映当前能力，不能夸大为完整 CRAN、完整 PDF/vignette 解析、真实 LLM 生成、生产级沙箱或替代统计专家审查。
- R/Docker 执行必须是 optional capability。不可用时返回 `skipped`，不能让核心测试失败。
- v0.4 repair loop 必须是 deterministic rule-based，不得自动联网安装 R 包，不得调用 LLM。
- 执行日志、reports、evaluation results、vector artifacts、processed corpus 和大文件不要提交。

## v0.6 Retrieval Evaluation 约束

- gold labels 必须小型、人工可审计；不得为了提升指标而修改 gold labels 或刻意拟合 query set。
- 评估测试不得联网，不得使用在线 LLM、LLM-as-a-judge、Ragas、DeepEval、LangSmith 或在线评测 SDK。
- 默认 vector evaluation 只能使用 `LocalHashEmbeddingBackend` 和 `NumpyVectorIndex`，不得要求 FAISS、sentence-transformers 或模型下载。
- TF-IDF、vector 和 hybrid 必须复用现有检索实现；完全同分时按 score descending、`chunk_id` ascending 稳定排序。
- metric implementation 修改必须配套精确单元测试，尤其是 graded gain、discount、duplicate IDs、invalid k 和空 relevance。
- `evaluation/results/` 运行产物不要提交；`evaluation/suites/` 与经实际重复验证的小型 baseline 可以提交。
- baseline 只能显式写入或覆盖，覆盖已有 baseline 必须使用 `--force`。
- README 和报告不得把 local-hash 指标描述为真实语义模型指标，不得把小型 benchmark 结论夸大到整个 R 生态或端到端代码质量。

## v0.5 Web Demo / FastAPI 约束

- Streamlit、FastAPI、uvicorn 只能放在 `web` optional dependencies，不能进入核心 dependencies。
- 默认测试不能启动真实浏览器、长期运行 Streamlit/FastAPI 服务、访问网络、依赖 API key、Docker/R、FAISS 或 sentence-transformers。
- Web 层必须调用现有 Agent pipeline，不复制 query rewrite、retrieval、generation、execution、diagnostics 或 repair 核心逻辑。
- 默认不执行 R；UI/API 中只有用户显式启用 `execute` 时才可尝试 Docker/R。
- Docker/R 不可用时 Web/API 必须返回或展示 `skipped`，不能让 demo 崩溃。
- UI 文案和公开文档不得夸大为生产级系统、生产级沙箱、真实在线 LLM 或统计专家审查替代品。
- 不提交 generated reports、processed corpus、vector artifacts、execution logs、`.test-output/` 或 `__pycache__/`。

## v0.4 Execution / Repair 约束

- 默认不执行 R。只有 `--execute` 才能尝试 Docker/R。
- Docker/R 不可用、镜像不存在或执行被安全检查阻止时，必须 graceful skipped 或返回 `unsafe`，不能抛出未捕获异常。
- Docker 限制参数只是可选受限执行原型，不是生产级安全边界，文档不得声称绝对安全。
- `diagnostics.py` 只能做离线字符串规则分类，测试使用 stderr/stdout fixtures，不依赖真实 R。
- `repair.py` 不能生成 `install.packages()`，不能自动联网安装包，不能盲目改列名。
- `repair_loop.py` 默认最多 one-shot repair，v0.4 不做多轮复杂 agent loop。
- repaired code 也必须再次经过静态安全检查。

## v0.3 Vector 层约束

- `faiss-cpu` 和 `sentence-transformers` 只能放在 `vector` optional dependencies，不能进入核心 dependencies。
- `LocalHashEmbeddingBackend` 是默认离线测试 backend。
- 测试不能下载 SentenceTransformer 模型或访问模型仓库。
- `NumpyVectorIndex` 是默认本地 fallback。
- `FaissVectorIndex` 必须延迟 import `faiss`，并在未安装时提示 `py -3 -m pip install -e ".[vector]"`。
- `knowledge/artifacts/` 中的生成文件不要提交，尤其是 `*.index`、`*.faiss`、`*.npy`、`*.json`、`*.jsonl`、`*.pkl`、`*.parquet`。
- 保留 `knowledge/artifacts/.gitkeep`。

## v0.2 Data 层约束

- `data/raw/fixtures/` 保存小型 HTML fixtures，用于离线 parser 测试和 offline build。
- `data/raw/cran_packages.json`、`data/processed/*.jsonl` 是可生成产物，不要提交大文件、下载缓存、源码 tarball 或 PDF。
- v0.2 只解析 CRAN package page metadata，不解析完整 PDF 正文，不下载源码 tarball，不解析完整 vignette 内容。
- `corpus_loader` 必须优先加载 `data/processed/corpus.jsonl`，不存在时回退到 `rstats_agent/knowledge/fixtures/r_core_corpus.jsonl`。

## Fixture Schema

知识库 chunk 至少包含：

- `chunk_id`
- `package`
- `function`
- `source_type`
- `title`
- `text`
- `source_url`
- `license`
- `provenance`
- `priority`

v0.2/v0.3 processed corpus 可额外包含 `package_version`、`published`。Retrieval results 可额外包含 `retriever`、`vector_score`、`lexical_score`。v0.4/v0.5 responses 可额外包含 `execution_diagnostics`、`repair_suggestions`、`repair_loop`、`markdown_report`。

## 常用命令

```powershell
py -3 -m pytest -q
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，按 store 和 month 汇总 revenue" --no-execute
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，删除 price 缺失并按 store 汇总 revenue" --execute --repair --max-repairs 1
py -3 data/crawl_cran_packages.py --offline-fixtures --output data/raw/cran_packages.json
py -3 data/build_corpus.py --input data/raw/cran_packages.json --output data/processed/corpus.jsonl
py -3 data/build_license_ledger.py --input data/raw/cran_packages.json --output data/processed/licenses.jsonl
py -3 data/build_vector_index.py --backend local-hash --index-backend numpy --output-dir knowledge/artifacts
py -3 -m streamlit run app/ui_streamlit.py
py -3 -m uvicorn app.api_fastapi:app --reload
py -3 scripts/evaluate_retrieval.py --suite evaluation/suites/core_functions.jsonl --corpus-profile fixture-core --retrievers tfidf vector hybrid --k 1 3 5 --output-dir evaluation/results
py -3 scripts/evaluate_retrieval.py --suite evaluation/suites/core_functions.jsonl --corpus-profile fixture-core --retrievers tfidf vector hybrid --k 1 3 5 --compare-baseline evaluation/baselines/v0.6_core_functions.json --max-regression 0.02
```

## 不做的事

- 不在测试中联网。
- 不自动安装 R 包。
- 不自动下载 Docker 镜像。
- 不下载 SentenceTransformer 模型作为测试前置。
- 不把 fixture 当成完整官方文档。
- 不把 optional Docker/R 执行描述为生产级沙箱。
- 不把 optional Web UI / FastAPI 描述为生产级服务。
- 不把 local-hash retrieval benchmark 描述为生产语义模型评估。
- 不自动更新 gold labels 或 retrieval baseline。
