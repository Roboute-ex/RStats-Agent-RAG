# RStats-Agent-RAG v0.5 Demo Script

## 一句话介绍

`RStats-Agent-RAG` 是一个 local-first、offline-test-first 的 R 统计 Agent/RAG 原型：把中文或英文统计分析需求转成可审计的 R 代码，并给出解释、输入假设、引用片段、可选执行状态、错误诊断和规则化修复建议。

## 版本演进

- v0.1：fixture corpus、query rewrite、TF-IDF retrieval、template generator、静态 safety、CLI 和 Markdown report。
- v0.2：CRAN package metadata parser、offline fixtures、processed corpus、license ledger 和 provenance。
- v0.3：embedding backend、本地 local hash embedding、numpy vector index、optional FAISS 和 hybrid retrieval。
- v0.4：optional Docker/R execution、structured diagnostics、rule-based repair suggestions 和 one-shot repair loop。
- v0.5：optional Streamlit interactive demo、optional FastAPI service、built-in demo cases 和 report download。

## Streamlit Demo

1. 安装可选 Web 依赖：

```powershell
py -3 -m pip install -e ".[dev,web]"
```

2. 启动 UI：

```powershell
py -3 -m streamlit run app/ui_streamlit.py
```

3. 在 sidebar 选择 demo case、retriever、execute、repair、max repairs 和 top k。
4. 默认不要勾选 execute，先展示纯离线 Agent/RAG 生成路径。
5. 点击 Run 后展示 R code、explanation、assumptions、failure modes、citations、execution status 和 Markdown report 下载。
6. 如果勾选 execute 但 Docker/R 不可用，说明状态会 graceful skipped，不影响 demo。

## FastAPI Demo

1. 启动服务：

```powershell
py -3 -m uvicorn app.api_fastapi:app --reload
```

2. 打开接口文档：

```text
http://127.0.0.1:8000/docs
```

3. 演示 `GET /health`，确认版本和服务状态。
4. 演示 `GET /demo-cases`，展示内置案例列表。
5. 演示 `POST /analyze`，默认 `execute=false`，返回 R code、解释、引用、执行状态和 Markdown report。

## Local-first / Offline-test-first 讲法

- 默认不调用在线 LLM，不依赖 OpenAI API 或 API key。
- 默认测试不访问网络，不要求真实 CRAN 下载、本机 R、Docker、FAISS 或 sentence-transformers。
- Streamlit、FastAPI 和 uvicorn 都是 optional web dependencies，不进入核心依赖。
- 知识库优先使用 processed corpus，缺失时回退 fixture corpus。

## 安全执行和 Repair Loop 边界

- 默认不执行 R，只有显式 `--execute` 或 UI/API 参数 `execute=true` 才尝试 Docker/R。
- Docker/R 不可用、镜像缺失或安全检查阻止时返回 `skipped` 或 `unsafe`，不让核心流程崩溃。
- Docker 参数只是受限执行原型，不是生产级安全沙箱。
- repair loop 是 deterministic rule-based one-shot，不调用 LLM，不自动 `install.packages()`，不联网安装 R 包，也不盲目修改列名。

