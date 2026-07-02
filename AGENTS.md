# AGENTS.md

本项目是 `RStats-Agent-RAG`，当前版本为 v0.3。本仓库优先保持本地、可审计、可测试、Windows PowerShell 友好。

## 工作原则

- 测试必须 deterministic，不能访问网络，不能依赖 API key、真实 CRAN 下载、本机 R、Docker 或 FAISS。
- 默认不调用在线 LLM；不要引入 OpenAI、Milvus、Weaviate、Streamlit、FastAPI、repair loop 等非 v0.3 功能。
- README 和公开文档必须真实反映当前能力，不能夸大为完整 CRAN、完整 PDF/vignette 解析、真实 LLM 生成、生产级沙箱或替代统计专家审查。
- R/Docker 执行必须是 optional capability。不可用时返回 `skipped`，不能让核心测试失败。
- 真实 CRAN crawl 只允许通过开发者手动命令运行；测试和默认流程必须使用 offline fixtures。
- 测试不能下载 SentenceTransformer 模型。
- 如果 FAISS 不存在，测试应验证清晰错误或跳过 optional 路径；不能要求本机默认安装 FAISS。

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

v0.2/v0.3 processed corpus 可额外包含 `package_version`、`published`。Retrieval results 可额外包含 `retriever`、`vector_score`、`lexical_score`。

## 常用命令

```powershell
py -3 -m pytest -q
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，按 store 和 month 汇总 revenue" --no-execute
py -3 data/crawl_cran_packages.py --offline-fixtures --output data/raw/cran_packages.json
py -3 data/build_corpus.py --input data/raw/cran_packages.json --output data/processed/corpus.jsonl
py -3 data/build_license_ledger.py --input data/raw/cran_packages.json --output data/processed/licenses.jsonl
py -3 data/build_vector_index.py --backend local-hash --index-backend numpy --output-dir knowledge/artifacts
```

## 不做的事

- 不在测试中联网。
- 不自动安装 R 包。
- 不自动下载 Docker 镜像。
- 不下载 SentenceTransformer 模型作为测试前置。
- 不把 fixture 当成完整官方文档。
