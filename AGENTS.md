# AGENTS.md

本项目是 `RStats-Agent-RAG` 的 v0.1，本地 MVP 优先。后续 Agent 或开发者在本仓库工作时，请遵守以下约束。

## 工作原则

- 保持 deterministic：测试不得依赖外网、API key、真实 CRAN 下载、本机 R 或 Docker。
- 默认不调用在线 LLM。生成逻辑优先使用明确规则、模板或可测试的小函数。
- R/Docker 执行必须是 optional capability。不可用时返回 `skipped`，不要让核心测试失败。
- 不要在测试中隐式拉取 Docker 镜像或安装 R 包。
- 对 R 代码执行前必须经过 `execution.safety.check_r_code_safety`。

## 代码风格

- 尽量使用标准库 dataclass，避免不必要依赖。
- 新模块应保持小而清晰，优先扩展现有 pipeline：rewrite -> retrieve -> fuse -> generate -> safety/execute -> report。
- 新 fixture 必须包含 `chunk_id`、`package`、`function`、`source_type`、`title`、`text`、`source_url`、`license`、`provenance`、`priority`。
- 离线测试语料应使用 `license: "synthetic_fixture"` 和 `provenance: "handwritten_summary_for_offline_tests"`，避免被误解为真实官方许可声明。
- 新测试应稳定、快速、离线。

## 常用命令

```powershell
py -3 -m pytest
py -3 -m rstats_agent.cli "请用 dplyr 清洗销售数据，按 store 和 month 汇总 revenue" --no-execute
```

## v0.1 不做的事

- 不做真实 CRAN 爬虫。
- 不接 Milvus、Weaviate 或外部向量数据库。
- 不要求用户机器必须安装 R 或 Docker。
- 不把 fixture 当成完整官方文档。
