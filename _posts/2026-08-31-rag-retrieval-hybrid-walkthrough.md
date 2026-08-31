---
layout: single
title: "RAG 学习笔记：Phase 3 hybrid.py 带读"
date: 2026-08-31 15:54:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - Hybrid检索
  - RRF
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 3 检索（第三篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/retrieval/hybrid.py` |
> | GitHub 原文 | [hybrid.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/hybrid.py) |
> | 上一篇 | [corpus.py + bm25.py]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) |
> | Phase 3 系列 | [types + vector]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) → [corpus + bm25]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) → **hybrid**（本文）→ [rerank + engine]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) → [收官]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) |
> | CLI | `python -m app.retrieval.search "..." --mode hybrid` |
>
> 全文 73 行。**这篇是先跟 AI 逐行读码、自己思考完，再整理成博客的**——不是一上来就看成品文档。记录的是 vector + bm25 两路榜单怎么合成一路、以及我读码时的真实卡点和纠错。

## 1. 读这文件之前，我已经知道什么？

[corpus + bm25 篇]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %})末尾留下一个问题：同一 query `"什么是 RAG？"`，vector Top-1 是 `2026-08-06-RAG.md`，bm25 Top-1 是 chunker 带读——**两路都有道理，谁该排第一？**

打开 `hybrid.py` 之前，我天真地想过：**把 vector 分 + bm25 分加起来不就行了？** 读完后才明白：vector ~0.65、bm25 ~7.2，刻度完全不同，没法直接加。

这个文件的角色用白话讲就是：

> **两个搜书助手**（vector 看语义、bm25 看关键词）各交一份 Top 15 推荐清单；**hybrid 是裁判**——不看原始分，只看排名，用 RRF 排出一份最终榜，再取 Top 5 给你。

## 2. 整体数据流（先建立全局感）

```
hybrid_search("什么是 RAG？")
    │
    ├─ k=5（最终返回几条）  fetch_k=15（融合前各取几条）
    │
    ├─ similarity_search(..., top_k=15)   ← vector 榜 Top15
    ├─ bm25_search(..., top_k=15)         ← bm25 榜 Top15
    │
    ├─ id_to_hit：两路 hits 合并去重 → 查正文用的「通讯录」
    │
    ├─ _rrf_merge：按 RRF 公式算融合分、重排序
    │
    └─ merged[:5]  ← 这才是最终 Top5
```

**我的第一个 breakthrough：** L58–63 **还没有**决定最终 Top5——只是「各取 15 + 建通讯录」；**L72 的 `merged[:k]` 才是截断**。我之前把「取前几个」全堆在 L58–63 理解，是读岔了。

## 3. 个人思考：只设 top_k=5 会漏什么？

读 L52–54 时，AI 问我：如果只设 `top_k=5`、没有 `fetch_k=15`，会漏掉什么样的 chunk？

**我第一遍的回答：** 会漏掉 vector 强 bm25 弱的，或者 vector 弱 bm25 强的。

**纠正后更精确的说法：**

> 漏掉的是：**在某一路里排第 6 名及以后，但在另一路里排很靠前** 的 chunk。

| chunk | vector 排名 | bm25 排名 | 只各取 top 5 |
| --- | --- | --- | --- |
| A | 第 1 | 第 8 | vector 有，bm25 没有 A |
| **B** | **第 9** | **第 2** | ❌ vector 没有 B，融合池进不去 |
| C | 第 3 | 第 4 | 两路都有 |

**B 就是典型**：bm25 认为它很相关（第 2），vector 只排到第 9——各取 5 的话 B 根本进不了 RRF。

### fetch_k=15 从哪来？漏掉能避免吗？

```python
fetch_k = candidate_k if candidate_k is not None else settings.retrieval_candidate_k  # 默认 15
```

- **15 是 config 里的工程默认值**（`retrieval_candidate_k`），不是算出来的最优解
- 对本库 hybrid 模式 Recall@3 已 100%，说明 15 够用
- **漏掉无法 100% 避免**——只要每路只取有限条，就总有 chunk 在两路都排得靠后。`fetch_k=15` 是**降低漏的概率**，不是消灭漏

| 情况 | 只取 top 5 | 取 top 15 |
| --- | --- | --- |
| vector 第 8、bm25 第 2 | ❌ | ✅ |
| vector 第 20、bm25 第 1 | ❌ | ❌ 仍可能漏 |

## 4. hybrid_search 逐段读

→ 源码 [hybrid.py L42–72](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/hybrid.py)

### 4.1 两个 k

```python
k = top_k if top_k is not None else settings.retrieval_top_k          # 5
fetch_k = candidate_k if candidate_k is not None else settings.retrieval_candidate_k  # 15
fetch_k = max(fetch_k, k)
```

| 变量 | 默认 | 人话 |
| --- | --- | --- |
| `k` | 5 | 最终给你几条 |
| `fetch_k` | 15 | 两个助手**各自**先报几个候选人 |

`max(fetch_k, k)` 是兜底：避免有人传 `top_k=10, candidate_k=5` 这种矛盾。

### 4.2 L58–63：两路各取 15 + 建通讯录

```python
vec_result = similarity_search(query, top_k=fetch_k, source_file=source_file)
bm25_result = bm25_search(query, top_k=fetch_k, source_file=source_file)

id_to_hit: dict[str, RetrievalHit] = {}
for hit in vec_result.hits + bm25_result.hits:
    id_to_hit.setdefault(hit.chunk_id, hit)
```

我画了两个榜才想通：

```
vector 榜（15人）          bm25 榜（15人）
#1  A                      #1  B
#2  B                      #2  D
#3  C                      #3  A
...                        ...
```

- `vec_result.hits` / `bm25_result.hits`：**各自内部已排好序**（search 函数里排的）
- L58–59 只是各取「自己榜上的前 15」
- L61–63 **不排序、不截断 Top5**，只是把最多 30 条去重存 dict，后面 RRF 算完分要用 `chunk_id` 查正文

**`setdefault` 复习：**

```python
id_to_hit.setdefault(hit.chunk_id, hit)
# 等价于：没有这个 id 才写入；有了就跳过
```

遍历顺序是 `vec_result.hits + bm25_result.hits`，所以**同 chunk 保留 vector 那份**。

### 4.3 调用 _rrf_merge

```python
merged = _rrf_merge(
    [ [h.chunk_id for h in vec_result.hits], [h.chunk_id for h in bm25_result.hits] ],
    rrf_k=settings.hybrid_rrf_k,
    id_to_hit=id_to_hit,
)
```

传给 RRF 的是**两串 chunk_id 名单**，不是 0.65 或 7.2 那种原始分——融合只看排名。

## 5. _rrf_merge：RRF 公式 + 我读错 enumerate 的经历

→ 源码 [hybrid.py L14–39](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/hybrid.py)

### 5.1 rrf_k 从哪来？怎么进公式？

```python
# config.py
hybrid_rrf_k: int = 60

# 公式里
1.0 / (rrf_k + rank)
```

**我原来的困惑：** `rrf_k` 是算出来的吗？怎么突然出现在分母里？

**搞懂之后：** 60 是 RRF 原论文的常用默认值，通过 `settings.hybrid_rrf_k` 传进来。它控制「排名差距有多平滑」——k 越大，第 1 名和第 10 名贡献差越小；k 越小，Top-1 优势越明显。

| rank | 贡献（k=60） |
| --- | --- |
| 第 1 名 | 1/61 ≈ 0.0164 |
| 第 2 名 | 1/62 ≈ 0.0161 |
| 第 10 名 | 1/70 ≈ 0.0143 |

### 5.2 L21–23 逐行 + 手算

```python
for ranks in ranked_lists:                    # 外层：vector 一路、bm25 一路
    for rank, chunk_id in enumerate(ranks, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
```

假设：

```python
ranked_lists = [
    ["A", "B", "C"],      # vector
    ["B", "D", "A"],      # bm25
]
rrf_k = 60
```

手算（k=60）：

```
# vector 路
A: 0 + 1/61 = 0.01639
B: 0 + 1/62 = 0.01613
C: 0 + 1/63 = 0.01587

# bm25 路（累加）
B: 0.01613 + 1/61 = 0.03252   ← 两路都靠前，最高
D: 0 + 1/62 = 0.01613
A: 0.01639 + 1/63 = 0.03226
```

最终 **B > A > C/D**——B 在 vector 第 2、bm25 第 1，两路都贡献大。

### 5.3 我对 enumerate 的最大误区（必读纠错）

**我一开始以为：** `enumerate` 会根据数据大小自动生成降序排名，`start=1` 是因为 0 对公式无效。

**纠正：**

| 错 | 对 |
| --- | --- |
| enumerate 会排序 | **不会**。它只给「列表里已有的顺序」贴 1、2、3… |
| 按数据大小生成排名 | **排名是 search 函数排好的**——`similarity_search` / `bm25_search` 返回的 `hits` 已经是「分高在前」 |
| start=1 因为 0 无效 | 半对：公式里 rank 从 1 计，所以用 `start=1`；但核心不是「0 无效」，是**第 1 个元素必须叫 rank=1** |

```
bm25_search 返回（已排好序）:
  hits = [B, D, A, ...]
           ↓ enumerate(start=1) 只贴标签
  rank=1→B, rank=2→D, rank=3→A
           ↓
  scores["B"] += 1/(60+1)
```

**谁排序？search 函数。enumerate 干什么？给「第几名」编号。**

### 5.4 排序 + 为什么要 new 一个 RetrievalHit？

```python
merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

和 [bm25 篇]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %})一样：`key=lambda x: x[1]` 按分数降序。

```python
for chunk_id, score in merged:
    base = id_to_hit[chunk_id]
    hits.append(RetrievalHit(..., score=score, rank_source="hybrid", ...))
```

**我的理解：** 因为要根据 vector + bm25 **混合之后的新分**来代表这一行——原来的 hit 带着 vector 的 0.65 或 bm25 的 7.2，和 `rank_source="vector"/"bm25"`，已经不能描述「融合榜上的这一行」了。

| 字段 | 融合前 | 融合后 |
| --- | --- | --- |
| `score` | 0.65 或 7.2 | **RRF 分 ~0.03** |
| `rank_source` | vector / bm25 | **hybrid** |
| `content` | 不变 | 从 `id_to_hit` 抄 |

如果直接改旧 hit：同一 chunk 可能有两份（vector 一份、bm25 一份），改哪个？CLI 显示 `[vector]` 也会误导。

## 6. 三句人话总结整文件

1. **两个助手各报 15 个候选，不是 5 个**——避免「一路强、一路排在第 6 名开外」的好段落进不了融合池。
2. **融合不看原始分，只看两榜排名**——RRF 公式 `1/(60+rank)`，出现几次加几次。
3. **融合完再取 Top5 返回**——15 是候选池，5 才是最终答案；hybrid 的 score 是 ~0.03 量级，别和 vector/bm25 比。

## 7. 本机实测

```bash
cd rag-backend && source .venv/bin/activate
python -m app.retrieval.search "什么是 RAG？" --mode vector --top-k 3
python -m app.retrieval.search "什么是 RAG？" --mode bm25 --top-k 3
python -m app.retrieval.search "什么是 RAG？" --mode hybrid --top-k 3
```

| 模式 | Top-1 | 耗时 |
| --- | --- | --- |
| vector | `2026-08-06-RAG.md` | ~4123ms |
| bm25 | chunker 带读 | ~286ms |
| hybrid | `2026-08-06-RAG.md`（score≈0.0325） | ~5373ms |

建议**三种模式都跑一遍**对比 Top-3，比只看 hybrid 的数字直观。

## 8. 和 engine.py 的关系（预告）

CLI 默认其实是 `hybrid_rerank`，不是单纯的 hybrid：

```
hybrid 取 ~15 候选 → reranker 精读「问题+段落」→ 最终 Top5
```

[engine.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/engine.py) 下一篇展开。

## 9. Phase 3 带读进度

| 文件 | 状态 |
| --- | --- |
| types.py + vector_store.py | ✅ [第一篇]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) |
| corpus.py + bm25.py | ✅ [第二篇]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) |
| **hybrid.py** | ✅ **本文** |
| [reranker.py + engine.py]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) | ✅ 已有博客 |
| [search.py + eval/]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) | ✅ [收官篇]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) |

## 10. 小结：这次读码的真实收获

1. Hybrid **不能** vector 分 + bm25 分——RRF 只看**排名**
2. `fetch_k=15` vs `top_k=5`——先多取候选再融合；漏 chunk **无法完全避免**，只能降低概率
3. L58–63 是「各取 15 + 通讯录」；**最终 Top5 在 L72 `merged[:k]`**
4. **`enumerate` 不排序**——search 已排好，enumerate 只贴「第几名」；`start=1` 让第 1 个元素对应 rank=1
5. **new RetrievalHit**——score 换成 RRF 分，`rank_source="hybrid"`
6. `rrf_k=60` 来自 config，是公式里的平滑常数，不是检索算出来的

下一篇：**[reranker.py + engine.py 带读]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %})** —— Cross-Encoder 精排、四种模式总地图。
