# RAG Backend

个人博客 RAG 智能问答系统 — 后端服务（FastAPI + LangGraph + Chroma + BGE-M3）

**当前阶段**：阶段 3 — 检索系统实现与优化 ✅（代码完成，待带读学习）

## 快速开始

```bash
cd rag-backend
source .venv/bin/activate

# 检索（默认 hybrid_rerank）
python -m app.retrieval.search "什么是 RAG？"
python -m app.retrieval.search "Docker 部署" --mode hybrid --top-k 3
python -m app.retrieval.search "BM25" --mode bm25

# 评测 Recall@K（四种模式对比）
python eval/run_eval.py
python scripts/verify_retrieval.py

# 全量索引博客（首次或重建知识库）
python -m app.ingestion.index --full

# 增量更新单篇文章
python -m app.ingestion.index --file 2026-08-06-RAG.md

# 查看库内 chunk 数量
python -m app.ingestion.index --stats

# 启动 API
python -m app.main
```

## 目录结构

```
rag-backend/
├── app/
│   ├── config.py
│   ├── main.py
│   ├── graph/              # LangGraph 工作流（阶段 4 扩展）
│   ├── ingestion/          # 阶段 2：数据入库
│   │   ├── loader.py … index.py
│   └── retrieval/          # 阶段 3：检索
│       ├── types.py        # RetrievalHit / RetrievalResult
│       ├── corpus.py       # Chroma 语料缓存
│       ├── vector_store.py # 向量检索
│       ├── bm25.py         # BM25 关键词检索
│       ├── hybrid.py       # RRF 融合
│       ├── reranker.py     # BGE-Reranker 精排
│       ├── engine.py       # 统一入口 search()
│       └── search.py       # 检索 CLI
├── eval/
│   ├── eval_set.json       # 24 条评测问答
│   └── run_eval.py         # Recall@1/3/5 批量评测
├── scripts/
│   ├── verify_chroma.py      # 阶段 1
│   ├── verify_embedding.py   # 阶段 1
│   ├── verify_ingestion.py   # 阶段 2
│   └── verify_retrieval.py   # 阶段 3
├── data/chroma/            # 向量库持久化
└── data/models/            # BGE-M3 本地模型
```

## 阶段 2 索引基线（本机实测 2026-08-30）

| 指标 | 数值 |
| --- | --- |
| 文章数 | 19 |
| chunk 总数 | 298 |
| 全量索引耗时 | ~534s（13 篇 / CPU，历史基线） |
| 增量单篇 | ~30–52s（视 chunk 数而定） |
| 增量旧文重索引 | 总数不膨胀（实测 179→179） |

## 阶段 2 验证

```bash
python scripts/verify_ingestion.py
```

验证项：metadata 六字段、1024 维向量、19 篇全部入库、`source_file` 过滤、检索探针（「什么是 RAG」→ Top-1 命中 `2026-08-06-RAG.md`）。

## 阶段 3 检索（2026-08-30 实测）

| 模式 | Recall@1 | Recall@3 | Recall@5 | avg 延迟 |
| --- | --- | --- | --- | --- |
| vector | 79.2% | 100% | 100% | ~909ms |
| bm25 | 79.2% | 100% | 100% | ~6ms |
| hybrid | 87.5% | 100% | 100% | ~746ms |
| **hybrid_rerank** | 75.0% | **95.8%** | 100% | ~87s* |

\* CLI 冷启动 + CPU Cross-Encoder；长驻进程预热后 vector/hybrid 约 sub-second，rerank 建议 GPU。

```bash
python scripts/verify_retrieval.py   # 四模式 smoke test
python eval/run_eval.py              # 完整 Recall 评测
```

## 分块策略

1. 按 `##` 标题切分（保留章节语义）
2. 超长 section 用 `RecursiveCharacterTextSplitter`（512 / overlap 64）
3. 代码块 ``` 尽量保持完整（占位符保护）
4. 每个 chunk 前缀：`【文章标题 > 章节标题】`

## 阶段 1 验证

```bash
python scripts/verify_chroma.py
python scripts/verify_embedding.py
python -m app.main   # /health
```

## 常见问题

**Q: Reranker 模型从哪来？**  
默认 `BAAI/bge-reranker-v2-m3`，首次运行自动下载。可设 `RERANKER_MODEL` 指向本地路径。

**Q: 全量索引很慢？**  
CPU 上 BGE-M3 约 8–15s/batch，298 chunk 全量约 9–15 分钟属正常。有 GPU 可在 `embedder.py` 开启 `use_fp16=True`。

**Q: 增量更新如何工作？**  
先 `delete(where source_file=xxx)` 删旧 chunk，再 upsert 新 chunk，不会重复累积。

**Q: socks 代理报错？**  
本地模型已在 `embedder.py` 自动跳过代理；`.env` 中 `EMBEDDING_MODEL` 务必指向本地路径。

**Q: ModelScope 下载锁冲突？**  
见下方 lock 清理步骤。

**Q: 一直显示 Still waiting to acquire lock？**

```bash
ps aux | grep download_model | grep -v grep   # 确认无重复进程
rm -rf data/models/.lock
find data/models -name '*.incomplete' -delete
python scripts/download_model.py
```
