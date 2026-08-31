---
layout: single
title: "RAG 学习笔记：Phase 3 收官 search + eval 与检索总览"
date: 2026-08-31 17:47:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - 检索评测
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 3 检索（收官篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `search.py`、`eval/eval_set.json`、`eval/run_eval.py`、`scripts/verify_retrieval.py` |
> | GitHub 原文 | [search.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/search.py) · [run_eval.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/eval/run_eval.py) |
> | 上一篇 | [reranker.py + engine.py]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) |
> | Phase 3 系列 | [types+vector]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) → [corpus+bm25]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) → [hybrid]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) → [rerank+engine]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) → **search+eval 总览（本文）** |
>
> **这篇不按行抠代码。** 前几篇已经把 vector / bm25 / hybrid / rerank 读完了；读 `search.py` 和 `eval/` 时发现主要是「命令行入口 + 自动阅卷」，Python 新语法点不多。本篇用大白话收束 **Phase 3 到底干什么、各文件分工、四种模式怎么选、怎么验收**。

## 1. Phase 3 一句话

> **用户提问 → 从博客库里找出最相关的几段话**（以后 Phase 4 再交给 LLM 生成回答）。

Phase 2 把文章切成小段写进 Chroma（建库）；Phase 3 是从库里**查出来**。

## 2. 各文件干什么？（一张表）

| 文件 | 大白话 |
| --- | --- |
| [types.py]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) | 一条搜索结果长什么样：正文、来源文章、分数、标签 |
| [vector_store.py]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) | **看意思搜**：embed 问题 → Chroma 比相似度（慢，懂语义） |
| [corpus.py + bm25.py]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) | **看关键词搜**：词在正文里出现多少（快，懂原词） |
| [hybrid.py]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) | **两路榜单合并**：RRF 按排名融合，不直接加 0.65 和 7.2 |
| [reranker.py]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) | **精读复查**：对 ~15 段候选逐对打分，筛成最准的 5 段 |
| [engine.py]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) | **总开关**：四种 mode 选谁、怎么串 |
| **search.py** | **终端命令**：你提问 → 调 engine → 打印结果 |
| **eval/** | **考试卷 + 自动批改**：24 题，算 Recall@K |
| verify_retrieval.py | **快速自检**：四种 mode 各跑 1 题，确认能跑 |

## 3. 四种模式：记一句口诀

| 模式 | 人话 | 典型标签 |
| --- | --- | --- |
| vector | 只看意思像不像 | `[vector]` |
| bm25 | 只看词有没有对上 | `[bm25]` |
| hybrid | 两个榜单合在一起 | `[hybrid]` |
| **hybrid_rerank**（**CLI 默认**） | 先合并，再精读 | `[rerank]` |

**口诀：** vector 看意思，bm25 看词，hybrid 合榜单，hybrid_rerank 合完再精读。

### 默认模式下一次查询怎么走

```
你: python -m app.retrieval.search "什么是 RAG？"
        ↓
search.py → engine (hybrid_rerank)
        ↓
vector 各取 15 + bm25 各取 15 → RRF 合并成 15 段
        ↓
Cross-Encoder 精读 15 对 [问题, 正文] → Top 5
        ↓
终端显示 #1 #2 #3…
```

## 4. search.py：终端入口（77 行，薄）

和 [index.py]({% post_url 2026-08-30-rag-ingestion-index-walkthrough %}) 一样：**自己不检索，只解析参数 → 调函数 → 打印**。

```bash
cd rag-backend && source .venv/bin/activate
python -m app.retrieval.search "什么是 RAG？"                    # 默认 hybrid_rerank
python -m app.retrieval.search "Docker" --mode bm25 --top-k 3
python -m app.retrieval.search "分块" --file 2026-08-29-rag-ingestion-chunker-walkthrough.md
```

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| `query` | 必填 | 用户问题 |
| `--mode` | hybrid_rerank | 四种检索策略 |
| `--top-k` | 5 | 返回几条 |
| `--file` | 无 | 只在某篇文章内搜 |

核心就一行：`result = search(args.query, mode=..., top_k=..., source_file=args.file)`。

## 5. eval：怎么证明检索「好不好」

### eval_set.json（24 条）

```json
{
  "id": "q03",
  "query": "chunk_overlap 重叠有什么作用？",
  "expected_sources": ["chunker-walkthrough.md", "blog-data-processing.md"]
}
```

- `expected_sources` 可以是**多篇**：Top-K 里命中**任意一篇**即算对
- 题目覆盖 RAG 原理、ingestion 系列、Docker/Redis、RRF/Reranker 等

### Recall@K 在本项目里的意思

> 24 道题里，有多少题在**前 K 条结果**里至少出现一篇期望文章。

| 指标 | 人话 |
| --- | --- |
| Recall@1 | Top-1 那篇对不对 |
| Recall@3 | Top-3 里有没有期望文章 |
| Recall@5 | Top-5 里有没有 |

**Recall@3 = 95.8%** ≈ 24 题里约 **23 题**在前 3 条里命中。项目验收线：**≥ 70%**。

### run_eval.py vs verify_retrieval.py

| | verify_retrieval | run_eval |
| --- | --- | --- |
| 干什么 | smoke test：能跑吗 | 完整评测：好不好 |
| 题数 | 1 条 | 24 条 |
| 判定 | Top-1 必须是 `2026-08-06-RAG.md` | 每题有自己的 expected_sources |

```bash
python scripts/verify_retrieval.py              # 改完代码先跑这个
python eval/run_eval.py                         # 四种 mode 对比表
python eval/run_eval.py --mode hybrid_rerank --verbose   # 看没命中的题
```

## 6. 本机验收数据（2026-08-30）

| 模式 | Recall@1 | Recall@3 | Recall@5 |
| --- | --- | --- | --- |
| vector | 79.2% | 100% | 100% |
| bm25 | 79.2% | 100% | 100% |
| hybrid | 87.5% | 100% | 100% |
| **hybrid_rerank** | 75.0% | **95.8%** | 100% |

hybrid_rerank 的 Recall@1 略低，但 **Recall@3 仍远高于 70% 验收线**——日常默认用它合理。

## 7. 读 Phase 3 的真实感受

前几篇（types、bm25、hybrid、rerank）Python 语法和概念密度高，值得逐行读。**search + eval 相对薄**：argparse、`engine.search` 调用、JSON 评测循环——**理解分工即可，不必再逐行抠**。

值得带走的 4 个点（面试/以后改代码）：

1. vector 和 bm25 **分数不能直接加** → hybrid（RRF）
2. rerank **不能对全库 298 条做** → 只对 hybrid 的 ~15 条候选
3. CLI 默认 **hybrid_rerank**，不是 vector
4. Phase 3 **只负责找段落**，还不生成回答（Phase 4）

## 8. Phase 3 在整个项目里的位置

```
Phase 0  文档           ✅
Phase 1  环境验证       ✅
Phase 2  数据入库       ✅  （7 篇带读）
Phase 3  检索           ✅  （5 篇：types/vector · corpus/bm25 · hybrid · rerank/engine · 本文收官）
Phase 4  LangGraph 问答 ⏳  下一步
Phase 5  前端 Widget    ⏳
Phase 6  集成测试       ⏳
Phase 7  部署上线       ⏳
```

## 9. Phase 3 带读进度（完结）

| 文件 | 博客 |
| --- | --- |
| types.py + vector_store.py | ✅ [第一篇]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) |
| corpus.py + bm25.py | ✅ [第二篇]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) |
| hybrid.py | ✅ [第三篇]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) |
| reranker.py + engine.py | ✅ [第四篇]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) |
| search.py + eval/ | ✅ **本文收官** |

## 10. 小结

Phase 3 = **建好的博客库 + 四种搜法 + 默认 hybrid_rerank + eval 验收**。代码带读系列到此收束；下一步 **Phase 4**：LangGraph 把检索到的 chunk 拼进 prompt，调 LLM 流式回答，提供 `/chat` API。
