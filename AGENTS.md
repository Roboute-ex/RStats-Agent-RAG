# AGENTS.md

本项目是 `RStats-Agent-RAG`，当前版本为 v0.2。本仓库优先保持本地、可审计、可测试、Windows PowerShell 友好。

## 工作原则

- 测试必须 deterministic，不能访问网络，不能依赖 API key、真实 CRAN 下载、本机 R 或 Docker。
- 默认不调用在线 LLM；不要引入 OpenAI、BGE、FAISS、Milvus、Weaviate 作为 v0.2 功能。
- R/Docker 执行必须是 optional capability。不可用时返回 `skipped`，不能让核心测试失败。
- 真实 CRAN crawl 只允许通过开发者手动命令运行；测试和默认流程必须使用 offline fixtures。
- 对 R 代码执行前必须经过 `execution.safety.check_r_code_safety`。

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

v0.2 processed corpus 可额外包含 `package_version`、`published`。

v0.1 离线测试语料应使用 `license: "synthetic_fixture"` 和 `provenance: "handwritten_summary_for_offline_tests"`，避免被误解为真实官方许可声明。

## 常用命令

```powershell
py -3 -m pytest -q
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，按 store 和 month 汇总 revenue" --no-execute
py -3 data/crawl_cran_packages.py --offline-fixtures --output data/raw/cran_packages.json
py -3 data/build_corpus.py --input data/raw/cran_packages.json --output data/processed/corpus.jsonl
py -3 data/build_license_ledger.py --input data/raw/cran_packages.json --output data/processed/licenses.jsonl
```

## 不做的事

- 不在测试中联网。
- 不自动安装 R 包。
- 不自动下载 Docker 镜像。
- 不把 fixture 当成完整官方文档。
