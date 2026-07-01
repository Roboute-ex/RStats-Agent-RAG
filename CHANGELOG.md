# Changelog

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
