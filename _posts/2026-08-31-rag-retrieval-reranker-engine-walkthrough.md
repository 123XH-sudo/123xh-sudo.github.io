---
layout: single
title: "RAG 学习笔记：Phase 3 reranker.py + engine.py 带读"
date: 2026-08-31 17:03:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - Reranker
  - Cross-Encoder
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 3 检索（第四篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/retrieval/reranker.py`、`engine.py` |
> | GitHub 原文 | [reranker.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/reranker.py) · [engine.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/engine.py) |
> | 上一篇 | [hybrid.py]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) |
> | Phase 3 系列 | [types + vector]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) → [corpus + bm25]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) → [hybrid]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) → **rerank + engine**（本文）→ [收官]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) |
> | CLI | `python -m app.retrieval.search "..."`（默认 `hybrid_rerank`） |
>
> reranker 80 行 + engine 54 行。**先逐行读码、自己思考，再整理成博客。** 这篇记录 Cross-Encoder 精排、四种检索模式怎么串、以及读码时把模式搞混的纠错。

## 1. hybrid 之后为什么还要 rerank？

[hybrid 篇]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %})末尾：RRF 融合后 #1 和 #2 的 score 可能都是 **0.0325**——**分一样，谁更该第一？** RRF 只看两榜排名，不会重新读「问题和这段正文到底有多贴」。

**reranker 的角色：** 精读裁判——把 hybrid 筛出的 ~15 条候选，逐对送进 Cross-Encoder 重打分、重排序。

```
vector ──┐
         ├── hybrid（粗排 ~15 条）──► reranker（精读 ~5 条）──► 最终答案
bm25  ──┘
```

终端默认 `--mode hybrid_rerank`，不是单纯的 `hybrid`——**engine.py 负责把这两步串起来**。

## 2. Bi-Encoder vs Cross-Encoder（读 reranker 前的概念卡）

Phase 2 [embedder 篇]({% post_url 2026-08-29-rag-ingestion-embedder-walkthrough %})学过 **Bi-Encoder（BGE-M3）**：

```
问题 ──embed──► 向量 A
正文 ──embed──► 向量 B
相似度 = A 和 B 的距离
```

**Cross-Encoder（BGE-Reranker）** 不同：

```
[问题, 正文] ──一起送进模型──► 一个相关分
```

| | Bi-Encoder（vector） | Cross-Encoder（reranker） |
| --- | --- | --- |
| 输入 | 问题、正文**分开** embed | `[问题, 正文]` **成对**输入 |
| 速度 | 快，可搜全库 298 条 | 慢，只对 Top-N 精排 |
| 精度 | 粗筛够用 | 更准，适合二次排序 |

**我的用词纠错：** 一开始说 rerank 是「对问题和回答同时进行向量化」——不对。Cross-Encoder **不是分别向量化再比距离**，是**成对一起读、直接打一个相关分**。

## 3. reranker.py 逐段读

→ 源码 [reranker.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/reranker.py)

### 3.1 模型单例 + 代理清理

```python
@lru_cache(maxsize=1)
def get_reranker_model():
    _clear_proxy_for_local_model()
    from FlagEmbedding import FlagReranker
    return FlagReranker(settings.reranker_model_path, use_fp16=False)
```

和 bm25 的 `@lru_cache`、embedder 的单例同一套路：**全进程只加载一次** reranker。本地模型时清 SOCKS 代理，Phase 1/2 踩过的坑。

### 3.2 核心：`rerank_hits`

#### 构造 pairs

```python
pairs = [[query.strip(), h.content] for h in hits]
scores = model.compute_score(
    pairs,
    batch_size=settings.rerank_batch_size,
    max_length=512,
)
```

**`compute_score` 是模型自带的吗？**  
是。**FlagEmbedding 库 `FlagReranker` 的方法**，不是项目自己写的（类似 embedder 调 `FlagModel.encode()`）。

**对每个 pair 怎么打分？** 对每个 `[问题, 正文]`：

1. 拼成模型输入（内部 tokenize）
2. 模型**一起读**问题和正文
3. 输出一个相关分（越高越相关）
4. 返回 `[score1, score2, ...]`，和 `pairs` **一一对应**

**`batch_size=8` 是什么？**  
15 条候选 = 15 个 pair。不必一次算 1 个——**每批最多 8 对一起送进模型**（默认 `rerank_batch_size=8`）。15 条会分成 `[8] + [7]` 两批，比 15 次单独算快。和 embedder 批量 embed 同一思路。

**`max_length=512`：** 一对 `[问题, 正文]` 太长会截断，和 chunk_size 同一量级。

#### 分数可能是单个 float

```python
if not isinstance(scores, list):
    scores = [scores]
```

只有 1 条候选时，库有时返回单个数而不是 list，这里统一成 list。

#### 排序 + new RetrievalHit

```python
scored = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)
for hit, score in scored[:k]:
    result.append(RetrievalHit(..., score=float(score), rank_source="rerank", ...))
```

| 语法 | 含义 |
| --- | --- |
| `zip(hits, scores)` | 第 i 个 hit 配第 i 个 rerank 分 |
| `scored[:k]` | rerank 后只取 Top 5（默认 k=5） |

**`hits` 是 hybrid 传过来、已经排好的吗？**  
engine 调用：`rerank_hits(query, hybrid_result.hits, top_k=k)`。✅ 来自 hybrid，✅ 已按 RRF 排好。但 rerank **不会沿用** hybrid 顺序——`compute_score` 重新打分，`sorted` 后按 rerank 分重排，原来的 #3 可能变 #1。

**rerank 之后还要 new RetrievalHit 吗？**  
**要。** 我第一遍说「不用吧，说不上来」——搞懂后和 hybrid 一样：

| 字段 | hybrid 给的 hit | rerank 之后 |
| --- | --- | --- |
| `score` | RRF ~0.03 | **rerank 分**（另一套刻度） |
| `rank_source` | `"hybrid"` | **`"rerank"`** |
| `content` | 不变 | 从原 hit 复制 |

不改的话 CLI 还显示 `[hybrid]`、score 还是 0.0325，和实际不符。

### 3.3 `rerank_search` vs engine 实际调用

`rerank_search` 包装成 `RetrievalResult` 并单独计时。**engine.py 直接调 `rerank_hits`**，在外层计总耗时——少包一层。

## 4. engine.py：四种模式的总调度

→ 源码 [engine.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/engine.py)

```python
SearchMode = Literal["vector", "bm25", "hybrid", "hybrid_rerank"]

def search(query, mode="hybrid_rerank", top_k=None, *, source_file=None):
```

| mode | 调谁 | 返回几条 |
| --- | --- | --- |
| `vector` | `similarity_search` | top_k（5） |
| `bm25` | `bm25_search` | top_k（5） |
| `hybrid` | `hybrid_search` | top_k（5） |
| **`hybrid_rerank`** | hybrid → rerank | **先 15 再 5** |

### hybrid_rerank 分支（最易读错）

```python
hybrid_result = hybrid_search(
    query,
    top_k=settings.retrieval_candidate_k,   # ← 15，不是 5！
    source_file=source_file,
)
reranked = rerank_hits(query, hybrid_result.hits, top_k=k)  # ← k=5
```

| 步骤 | 含义 |
| --- | --- |
| `hybrid_search(top_k=15)` | hybrid 的 `merged[:15]` → **RRF 后 15 条** |
| `rerank_hits(top_k=5)` | 15 对 Cross-Encoder 精排 → **最终 5 条** |

**和 hybrid.py 里 `fetch_k=15` 是一回事吗？**  
**不是。** 我读码时的理解：

| 概念 | 阶段 | 含义 |
| --- | --- | --- |
| `fetch_k=15` | hybrid **内部** | vector / bm25 **各自**取 15 |
| hybrid 返回 15 条 | hybrid **输出** | RRF **之后**的前 15 |
| 最终 5 条 | rerank **输出** | 15 条里精排 Top 5 |

engine 传 `top_k=15` 给 hybrid，是告诉 hybrid「RRF 后给我 15 条候选」，不是改 fetch_k。

## 5. 四种模式总地图（防混）

学完 Phase 3 前半，四种 mode 我确实混了。整理成一张表：

```
用户问："什么是 RAG？"
```

**vector** — 只看语义

```
问题 embed → Chroma 相似度 → Top 5   [vector]  score ~0.65
```

**bm25** — 只看关键词

```
分词 → BM25 全库打分 → Top 5   [bm25]  score ~7.2
```

**hybrid** — 两路榜单 RRF 合并

```
vector Top15 ──┐
               ├─ RRF → Top 5   [hybrid]  score ~0.03
bm25 Top15  ──┘
```

**hybrid_rerank** — 默认，粗排 + 精读

```
vector Top15 ──┐
               ├─ RRF → 15 条 [hybrid]
bm25 Top15  ──┘
        ↓
  Cross-Encoder 15 对打分
        ↓
      Top 5 [rerank]
```

**口诀：** vector 看意思，bm25 看词，hybrid 合榜单，hybrid_rerank 合完再精读。

### 和文件的对应

```
search.py (CLI，下一篇细读)
    └── engine.search(mode=...)
            ├── vector        → vector_store
            ├── bm25          → bm25
            ├── hybrid        → hybrid
            └── hybrid_rerank → hybrid(15) → reranker
```

## 6. 为什么不对全库 298 条 rerank？

**我的第一遍回答：** 要成对处理，精准但慢，所以先选最像的几个再精排——**方向对。**

补精确：**Cross-Encoder 每对 `[问题, 正文]` 都要跑一遍模型**。298 条全做 ≈ 298 次推理，CLI 上 hybrid_rerank 冷启动已经 ~87s 量级（CPU）；298 条不可接受。所以 **hybrid 粗筛 15 → rerank 精读 5**，准度和效率的折中。

## 7. 验证命令

```bash
cd rag-backend && source .venv/bin/activate

# 默认 hybrid_rerank（第一次慢，要加载 reranker）
python -m app.retrieval.search "什么是 RAG？" --top-k 3

# 对比纯 hybrid（无 rerank，快很多）
python -m app.retrieval.search "什么是 RAG？" --mode hybrid --top-k 3
```

看 `[hybrid]` vs `[rerank]` 标签，以及 Top-1 是否变化。

## 8. Phase 3 带读进度

| 文件 | 状态 |
| --- | --- |
| types.py + vector_store.py | ✅ [第一篇]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) |
| corpus.py + bm25.py | ✅ [第二篇]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) |
| hybrid.py | ✅ [第三篇]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) |
| **reranker.py + engine.py** | ✅ **本文** |
| [search.py + eval/]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) | ✅ [收官篇]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) |

## 9. 小结

1. **`compute_score`** — FlagReranker 自带；对 `[问题, 正文]` 成对打分；`batch_size=8` 是分批推理
2. **hybrid 的 hits** 是 RRF 候选；rerank **重打分、重排序**，不沿用 hybrid 顺序
3. **298 条不全 rerank** — Cross-Encoder 慢，只对 ~15 条精排
4. **fetch_k=15 ≠ hybrid 返回 15 条** — 前者是输入各取 15，后者是 RRF 输出 15
5. **new RetrievalHit** — score 换 rerank 分，`rank_source="rerank"`
6. **CLI 默认 `hybrid_rerank`** — engine 里 hybrid(15) → rerank(5)

下一篇：**[Phase 3 收官 search + eval 总览]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %})** —— 大白话收束、Recall 验收、系列完结。
