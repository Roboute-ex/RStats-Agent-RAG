# Retrieval Evaluation

## 1. 评估目标

v0.6 为已有检索层提供完全离线、deterministic、可审计的回归基准。它统一比较 TF-IDF、local-hash + numpy vector 与 hybrid retrieval，只评估 chunk ranking，不评估 R 代码生成或执行正确性。

## 2. Suite 结构

每个 suite 是 UTF-8 JSONL，每行是一条独立 gold query：

- `evaluation/suites/core_functions.jsonl` 固定使用 `rstats_agent/knowledge/fixtures/r_core_corpus.jsonl`，包含 30 条 dplyr、ggplot2、lme4 query。
- `evaluation/suites/cran_metadata.jsonl` 包含 16 条 metadata query。运行时从四个本地 CRAN HTML fixtures 在内存中构建 16 个 corpus chunks。

测试和 CLI 不读取已有 `data/processed/corpus.jsonl`，因此本地 generated corpus 是否存在不会改变 benchmark。

## 3. Gold Relevance Schema

必填字段为 `query_id`、`query`、`suite`、`category`、`language`、`query_type` 和 `relevance`，`notes` 可选。`relevance` 是 `chunk_id -> grade`：

- 3：直接回答 query 的核心 chunk。
- 2：高度相关的支持 chunk。
- 1：辅助相关 chunk。
- 0：不相关，通常不应写入 gold map。

loader 会拒绝空 query、空 relevance、重复 query ID、负数或非整数 grade、未知 chunk ID、没有正 grade 的 query，以及不支持的 language/query type。

## 4. 指标公式

grade 大于 0 即视为 relevant。重复 retrieved ID 会保留首次出现的位置后去重，所有 k 必须大于 0。

- `Recall@k = top-k 命中的 relevant chunk 数 / 全部 relevant gold chunk 数`
- `HitRate@k = top-k 至少命中一个 relevant chunk 时为 1，否则为 0`
- `RR@k = 1 / 首个 relevant chunk 的 rank`；top-k 无命中时为 0
- `MRR@k` 是每条 query 的 `RR@k` 算术平均
- `DCG@k = sum((2^grade - 1) / log2(rank + 1))`，rank 从 1 开始
- `nDCG@k = DCG@k / ideal DCG@k`

overall、category、language 和 query type 都采用 query-level macro average，不按 category 大小或 relevance 数量加权。

## 5. Corpus Profiles

`fixture-core` 明确加载 v0.1 固定 core corpus，共 14 个 chunks。`cran-metadata` 调用现有 CRAN parser 和 corpus builder，从 `cran_dplyr.html`、`cran_ggplot2.html`、`cran_lme4.html`、`cran_renv.html` 构建 corpus，不访问网络、不写 processed corpus。

## 6. Retriever Profiles

- `tfidf`：复用 `LocalTfidfRetriever` 与现有 query rewrite、metadata bonus。
- `vector`：使用 `LocalHashEmbeddingBackend` 和内存中的 `NumpyVectorIndex`。
- `hybrid`：复用 `HybridRetriever` 的 lexical/vector score fusion，默认权重为 0.4/0.6。

评估不会加载 FAISS artifacts，也不会 import sentence-transformers。local-hash 只用于离线确定性和架构回归，不等同于真实语义 embedding model。

## 7. Baseline Workflow

先运行 benchmark 并检查 JSON/Markdown 报告，再显式写入 baseline：

```powershell
py -3 scripts/evaluate_retrieval.py --suite evaluation/suites/core_functions.jsonl --corpus-profile fixture-core --retrievers tfidf vector hybrid --k 1 3 5 --write-baseline evaluation/baselines/v0.6_core_functions.json --force
```

比较当前结果：

```powershell
py -3 scripts/evaluate_retrieval.py --suite evaluation/suites/core_functions.jsonl --corpus-profile fixture-core --retrievers tfidf vector hybrid --k 1 3 5 --compare-baseline evaluation/baselines/v0.6_core_functions.json --max-regression 0.02
```

baseline 记录项目版本、suite、corpus profile、retriever、k、aggregate metrics、query count 和 corpus chunk count。query/corpus 数量或 metric set 不一致时拒绝比较。任一 metric 的 `current - baseline` 小于负 tolerance 时退出码为 3。已有 baseline 只能通过 `--force` 覆盖。

## 8. 分析 Zero-hit Queries

先检查 query 的 gold IDs 与 retrieved IDs，再确认 query rewrite 是否保留关键 package/function 术语。随后检查 gold chunk 是否确实直接支持 query，以及同分 tie-break 是否稳定。zero-hit 是诊断入口，不应通过删除合理 gold labels 来消除。

## 9. 新增 Query

先选定固定 corpus 中真实存在的 target chunk，再写自然、独立且不泄露 chunk ID 的 query。保持 category、language 和 query type 覆盖，并在 `notes` 说明 grade 判断依据。新增后运行 dataset tests、两遍完整 benchmark 和 baseline structural check。

## 10. 修改 Gold Labels

gold label 修改必须基于 corpus 内容复核，并在 code review 中解释原标签为何错误或不完整。不得因为某个 retriever 未命中、指标下降或 baseline 失败而修改 relevance。测试不会自动重写 suite。

## 11. 当前限制

- 这是项目维护的小型 curated regression benchmark，不代表整个 R 生态。
- fixture corpus 和 CRAN metadata corpus 都很小。
- local-hash 不提供生产语义质量结论。
- v0.6 不评估 generator、R execution、repair loop 或端到端答案正确性。
- 指标差异未做统计显著性检验，检索指标提升不自动表示生成代码更正确。

## 12. 常见问题

**为什么不用在线 judge？** 默认测试必须离线、无 API key 且可重复；v0.6 只做可审计 ranking metrics。

**为什么不要求 hybrid 优于 TF-IDF？** 三种 retriever 的结果必须如实呈现，benchmark 不是优势演示。

**结果文件能提交吗？** `evaluation/results/` 下的 JSON/Markdown 运行产物不能提交；经过重复验证且无路径、时间戳或机器信息的小型 baseline 可以提交。

**如何改变 hybrid 权重？** 使用 `--hybrid-vector-weight` 与 `--hybrid-lexical-weight`。修改权重后应使用独立报告分析，不能静默覆盖 baseline。
