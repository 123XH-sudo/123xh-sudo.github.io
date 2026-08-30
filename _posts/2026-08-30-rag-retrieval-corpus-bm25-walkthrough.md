---
layout: single
title: "RAG 学习笔记：Phase 3 corpus.py + bm25.py 带读"
date: 2026-08-30 22:00:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - BM25
  - 关键词检索
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 3 检索（第二篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/retrieval/corpus.py`、`bm25.py` |
> | GitHub 原文 | [corpus.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/corpus.py) · [bm25.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/bm25.py) |
> | 上一篇 | [types.py + vector_store.py]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) |
> | Phase 3 系列 | [types + vector]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) → **corpus + bm25**（本文）→ hybrid → rerank/engine → eval |
> | CLI | `python -m app.retrieval.search "..." --mode bm25` |
>
> corpus 23 行 + bm25 79 行。vector 比「语义指纹」，BM25 比「关键词有没有出现」。这篇记录读码时的真实卡点和 Python 语法困惑（`lru_cache`、`zip`、`lambda`、Chroma `.get` 等）。

## 1. 为什么需要 BM25？

[上一篇 vector 带读]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %})里，检索靠 embed + Chroma 相似度。读 bm25 之前我的疑问是：**既然有 vector 了，为什么还要 BM25？**

| | vector | bm25（本文） |
| --- | --- | --- |
| 比什么 | 1024 维向量相似度 | 问题里的**词**在正文里出现多少 |
| 擅长 | 「RAG 是什么」≈「检索增强生成」 | `Docker`、`BM25`、`argparse` 等**原词** |
| 速度 | 慢（要 embed，~4s） | 快（纯算分，~286ms） |
| 谁提供 | Chroma `.query` | 第三方库 `rank_bm25` + 内存索引 |

本机实测同一问题 `"什么是 RAG？" --top-k 3`：

| 模式 | Top-1 | 耗时 |
| --- | --- | --- |
| vector | `2026-08-06-RAG.md` | ~4123ms |
| bm25 | `2026-08-29-rag-ingestion-chunker-walkthrough.md` | ~286ms |

两种都认为相关，但**排序不同**、**分数刻度不同**（vector ~0.65，bm25 ~7.2，不能直接比大小）。这就是后面 `hybrid.py` 要把两路结果融合的原因。

## 2. 整体数据流

```
bm25_search("什么是 RAG？")
    │
    ├─ _get_bm25_index()     ← 第1次：读全库 + 分词 + 建 BM25 索引（@lru_cache 缓存）
    │       └─ load_corpus() → collection.get() 读出全部 298 条
    │
    ├─ tokenize(问题)        ← ["什","么","是","rag"]
    │
    ├─ get_scores            ← 对 298 篇算 BM25 分
    │
    ├─ sorted + [:k]         ← Top-K 的 (下标, 分数)
    │
    └─ 用下标取 ids/documents → K 个 RetrievalHit → RetrievalResult
```

**关键纠正（我读码时的误区）：** `_get_bm25_index()` **不是**「根据问题返回 chunk」。它不管用户问什么，只做「把**全库**建成 BM25 索引」；**每个新问题**在后面 `get_scores(query_tokens)` 重新算分。

## 3. corpus.py：从 Chroma 读出全部语料

→ 源码 [corpus.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/corpus.py)

### 3.1 第 17–18 行：`collection.get` 是什么？

```python
data = collection.get(include=["documents", "metadatas"])
return data["ids"], data["documents"], data["metadatas"]
```

| 部分 | 含义 |
| --- | --- |
| `.get` | **Chroma 库自带方法**（不是 Python dict 的 get） |
| 不传 `where` | **取出 collection 里全部记录**（298 条） |
| `include=[...]` | 要哪些字段；这里要正文和 metadata，**不要 embedding** |

对比 Phase 2 / vector：

| 方法 | 干什么 |
| --- | --- |
| `.upsert` | 写入 |
| `.query` | 向量相似度搜 Top-K |
| `.get` | 取出记录（可全量，可 `where` 筛选） |

store 里按文章删旧 chunk 用过 `where`：

```python
collection.get(where={"source_file": "xxx.md"}, include=[])
```

corpus 这行**没写 where** = 全量读取，供 BM25 建索引。

### 3.2 `@lru_cache` 缓存什么？

```python
@lru_cache(maxsize=1)
def load_corpus() -> tuple[list[str], list[str], list[dict]]:
    ...
    return data["ids"], data["documents"], data["metadatas"]
```

| 次数 | 行为 |
| --- | --- |
| 第 1 次 | 真读 Chroma，返回 3 个 list |
| 第 2 次起（同进程） | 直接返回缓存，不再读盘 |

`invalidate_corpus_cache()` 在增量索引后应清缓存（目前 CLI 未自动调，知道即可）。

## 4. bm25.py：分词、建索引、算分

→ 源码 [bm25.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/bm25.py)

### 4.1 `BM25Okapi` 是系统自带的吗？会自动分词吗？

**都不是。**

```python
from rank_bm25 import BM25Okapi   # pip install rank-bm25
```

分词是项目自己的 `tokenize()`：

```python
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+")

def tokenize(text: str) -> list[str]:
    text = text.lower()
    return _TOKEN_RE.findall(text)
```

| 规则 | 匹配 |
| --- | --- |
| `[\u4e00-\u9fff]` | 一个汉字 |
| `[a-zA-Z0-9_]+` | 连续英文/数字/下划线 |

例：

```python
tokenize("什么是 RAG？")
# → ["什", "么", "是", "rag"]
```

中文是**单字** token，不是 jieba 整词。然后：

```python
tokenized = [tokenize(doc) for doc in documents]   # 298 篇各自的分词 list
BM25Okapi(tokenized)   # 吃「已分好词」的 list，不会自动分词
```

### 4.2 `_get_bm25_index()`（25–29 行）与第 48 行怎么衔接？

```python
@lru_cache(maxsize=1)
def _get_bm25_index():
    ids, documents, metadatas = load_corpus()
    tokenized = [tokenize(doc) for doc in documents]
    return BM25Okapi(tokenized), ids, documents, metadatas
```

```python
# bm25_search 第 48 行
bm25, ids, documents, metadatas = _get_bm25_index()
```

**第一次触发：** 你跑 `--mode bm25` 时，`bm25_search` 执行到第 48 行。

**缓存内容（和问题无关）：**

1. `BM25Okapi` 对象（全库索引）
2. `ids`、`documents`、`metadatas` 三个 list

**每个新问题：** 索引不变，只重新 `get_scores(query_tokens)` 算 298 个分再排序。

### 4.3 第 51–61 行：全库 vs 单篇，两种配对方式

#### 没加 `--file`（我终端走的路径）— else 分支

```python
scores = bm25.get_scores(query_tokens)
# scores 长度 298，scores[i] = 第 i 号 chunk 的分

ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
```

`enumerate(scores)` → `(0, 分0), (1, 分1), ...` 下标天然就是 chunk 编号。

#### 加了 `--file` — if 分支

```python
indices = [i for i, m in enumerate(metadatas) if m.get("source_file") == source_file]
scores = bm25.get_batch_scores(query_tokens, indices)
ranked = sorted(zip(indices, scores), key=lambda x: x[1], reverse=True)[:k]
```

`indices` 可能是 `[5, 6, 7, 12, ...]` **不连续**。此时 `scores[j]` 是 **`indices[j]` 那个 chunk** 的分，不是「第 j 号 chunk」的分。

| 写法 | 何时用 |
| --- | --- |
| `enumerate(scores)` | 全库：`scores[i]` 就是 chunk i |
| `zip(indices, scores)` | 单篇：真实下标在 `indices` 里，必须配对 |

**不能**在单篇分支写 `enumerate(scores)`，否则会把 `0,1,2` 误当成 chunk 编号，`ids[idx]` 会取错。

### 4.4 FAQ：`key=lambda x: x[1]` 为什么按第二项排？

`sorted` 排的是元组 `(下标, 分数)`：

```python
(0, 0.1), (1, 7.2), (2, 6.2), ...
 x[0] x[1]  x[0] x[1]
 下标  分数
```

要按**分数**从高到低 → `key=lambda x: x[1]`，`reverse=True`。

等价于：

```python
def get_score(pair):
    return pair[1]
sorted(..., key=get_score, reverse=True)
```

### 4.5 FAQ：`zip` 语法

```python
indices = [5, 6, 7]
scores  = [2.1, 7.0, 3.5]

zip(indices, scores)
→ (5, 2.1), (6, 7.0), (7, 3.5)
```

两个 list **按位置拉链配对**，长度必须相同。

## 5. 和 vector_store 的返回格式

BM25 最后同样：

```python
return RetrievalResult(query=query, hits=hits, elapsed_ms=elapsed_ms, mode="bm25")
```

`RetrievalHit` 里 `rank_source="bm25"`，`distance` 默认 `None`（没有向量距离）。

## 6. 验证命令

```bash
cd rag-backend && source .venv/bin/activate

python -m app.retrieval.search "什么是 RAG？" --mode vector --top-k 3
python -m app.retrieval.search "什么是 RAG？" --mode bm25 --top-k 3

# 只在单篇文章内 BM25（走 zip 分支）
python -m app.retrieval.search "incremental" --mode bm25 \
  --file 2026-08-30-rag-ingestion-pipeline-walkthrough.md
```

## 7. Phase 3 带读进度

| 文件 | 状态 |
| --- | --- |
| types.py + vector_store.py | ✅ [上一篇]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) |
| **corpus.py + bm25.py** | ✅ **本文** |
| hybrid.py | 待读 |
| reranker.py + engine.py | 待读 |
| search.py + eval/ | 待读 |

## 8. 小结

**读码收获：**

1. **corpus `.get` 无 where = 读全库**；BM25 要自己拿全部正文建索引，不像 vector 用 `.query`
2. **`_get_bm25_index` 建的是「整本词典」**，缓存的是全库索引 + 三个 list，**不是**某个问题的搜索结果
3. **`BM25Okapi` 来自 rank_bm25**，分词靠 `tokenize()`，中文单字 + 英文单词
4. **全库用 `enumerate(scores)`，单篇用 `zip(indices, scores)`** —— 因为下标是否连续
5. **`key=lambda x: x[1]`** = 按元组里第二项（分数）排序
6. vector 与 bm25 **Top-1 可能不同**，分数刻度不可比，需要 Hybrid 融合

下一篇：**hybrid.py** —— RRF 怎么把 vector 和 bm25 两路排名合在一起。
