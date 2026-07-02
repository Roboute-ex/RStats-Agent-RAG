# Changelog

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
- 更新 AGENTS，强调 README 必须真实反映当前能力，不得夸大完整 CRAN/PDF/vignette/LLM/生产沙箱支持。

## 0.2.0

- 新增 `data/` 层，用于 CRAN package page metadata 采集、raw 保存、processed corpus 构建和 license ledger 构建。
- 添加 dplyr、ggplot2、lme4、renv 的离线 CRAN HTML fixtures。
- 添加 CRAN parser、corpus builder、license ledger builder 的 deterministic 离线测试。
- 升级 corpus loader：默认优先加载 `data/processed/corpus.jsonl`，不存在时回退 v0.1 fixture corpus。
- 更新 README/AGENTS，明确 v0.2 只采集 metadata，不解析完整 PDF/vignette 正文，不下载源码 tarball。

## 0.1.0

- 初始化 `RStats-Agent-RAG` 本地 MVP。
- 添加 14 条 R 统计生态 fixture 知识片段，覆盖 dplyr、ggplot2、lme4。
- 实现 deterministic query rewriting。
- 实现基于 `TfidfVectorizer` 的本地 retriever 和 metadata 加权。
- 实现上下文融合、三类模板生成、静态 R 安全检查和可选 Docker R executor。
- 实现 CLI demo、Markdown 报告、examples 和 deterministic 测试。
