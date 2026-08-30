---
layout: single
title: "RAG 学习笔记：Phase 3 入门 types.py + vector_store.py"
date: 2026-08-30 21:00:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - 向量检索
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 3 检索（第一篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/retrieval/types.py`、`vector_store.py` |
> | GitHub 原文 | [types.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/types.py) · [vector_store.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/vector_store.py) |
> | Phase 2 完结 | [index.py 带读]({% post_url 2026-08-30-rag-ingestion-index-walkthrough %}) |
> | Phase 3 系列 | **types + vector**（本文）→ corpus/bm25 → hybrid → rerank/engine → eval |
> | CLI | [`python -m app.retrieval.search`](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/search.py) |
>
> 全文约 types 39 行 + vector_store 61 行。Phase 2 把 chunk **写进** Chroma，Phase 3 从 Chroma **查出来**。这篇记录读码时的真实卡点和 Python 语法困惑。

## 1. Phase 3 在整体里的位置

```
Phase 2 ingestion                    Phase 3 retrieval（本文起）
_posts → load/chunk/embed → Chroma
                               ↑
用户提问 → embed → query ──────┘  → Top-K chunk →（以后拼给 LLM）
              vector_store.py
```

**一句话：** `vector_store.py` 把用户问题变成向量，在向量库里做相似度搜索，返回 Top-K 条结果；`types.py` 定义「K 条结果长什么样」。

## 2. 读之前的困惑（真实记录）

1. `embed_texts([query.strip()])[0]` —— 为什么要包 list、为什么要 `[0]`？
2. `collection.query(**kwargs)` —— `.query` 从哪来？干什么？
3. 整体流程是线性的吗？第 38 行在整个文件里是什么角色？
4. `__init__` 老听到，dataclass 里却看不见，到底是什么？
5. `mode` 默认 `"vector"`，什么时候变？谁改？

下面按「先懂流程 → 再抠语法 → 再 FAQ」整理。

## 3. 整体流程（读 vector_store 前先建立地图）

以 `similarity_search("什么是 RAG？", top_k=5)` 为例：

| 步骤 | 行号 | 干什么 |
| --- | --- | --- |
| 空问题？ | 20–21 | 直接返回空结果 |
| 定 K | 23 | `k = 5` |
| 计时 | 24 | `t0 = time.perf_counter()` |
| **问题 → 向量** | 26 | `q_emb = embed_texts(...)[0]` |
| 连库 | 27–28 | `client` → `collection` |
| 填申请单 | 30–36 | 组装 `kwargs` dict |
| **真正查库** | 38 | `raw = collection.query(**kwargs)` |
| 停表 | 39 | `elapsed_ms` |
| 拆 raw | 42–45 | 取出 ids/docs/metas/dists |
| 组装 K 条 | 47–58 | 循环 → `RetrievalHit` |
| 打包返回 | 60 | `RetrievalResult` |

**第 38 行是分界线：** 之前都是准备；这一行是 Chroma 按向量相似度搜 Top-K；之后是整理结果。

## 4. types.py：Top-K 条结果长什么样

→ 源码 [types.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/types.py)

### 4.1 和 Phase 2 ChunkRecord 的对照

| | Phase 2 `ChunkRecord` | Phase 3 `RetrievalHit` |
| --- | --- | --- |
| 时机 | 写入库**之前** | 从库查**之后** |
| metadata | 每个字段单独一列 | 打包在一个 `dict` 里 |
| 额外字段 | 无 | `score`、`distance`、`rank_source` |

同一条 chunk：入库前叫 `ChunkRecord`，查出来包装成 `RetrievalHit`。

### 4.2 `@dataclass` 与 `RetrievalHit`

```python
@dataclass
class RetrievalHit:
    chunk_id: str
    content: str
    metadata: dict
    score: float = 0.0
    distance: float | None = None
    rank_source: str = ""
```

| 字段 | 含义 |
| --- | --- |
| `chunk_id` / `content` | Chroma 里的 id 和正文 |
| `metadata` | Phase 2 store 写入的 dict（source_file、post_title…） |
| `score` | **越大越相关**（全项目统一方向） |
| `distance` | **越小越相似**（仅 vector 有值，Chroma 原样） |
| `rank_source` | `"vector"` / `"bm25"` / …，标记来源 |

### 4.3 `@property` 快捷读 metadata

```python
@property
def source_file(self) -> str:
    return self.metadata.get("source_file", "")
```

`hit.source_file` 等价于 `hit.metadata.get("source_file", "")`，CLI 打印更简洁。

### 4.4 `RetrievalResult` — 一整包

```python
@dataclass
class RetrievalResult:
    query: str
    hits: list[RetrievalHit]   # ← Top-K 条在这里
    elapsed_ms: float
    mode: str = "vector"
```

调用者拿到：

```python
result.hits[0].content      # 第 1 条正文
result.hits[0].source_file  # 来自哪篇 md
len(result.hits)            # 实际几条（≤ K）
```

## 5. vector_store.py 关键行（语法 + 作用）

→ 源码 [vector_store.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/vector_store.py)

### 5.1 `q_emb = embed_texts([query.strip()])[0]`

从里到外：

```python
query.strip()           # 去首尾空格 → "什么是 RAG？"
[query.strip()]         # 包成 list → ["什么是 RAG？"]
                        # 因为 embed_texts 要求 list[str]
embed_texts(...)        # 返回 list[list[float]]，1 句 → 外层长度 1
[0]                     # 取第 1 个向量 → 1024 个 float 的一维 list
```

Phase 2 embed 的是 **chunk 文本**；Phase 3 embed 的是 **用户每个新问题**。

### 5.2 `kwargs` 与 `collection.query(**kwargs)`

```python
kwargs = {
    "query_embeddings": [q_emb],
    "n_results": k,
    "include": ["documents", "metadatas", "distances"],
}
raw = collection.query(**kwargs)
```

- `collection` 来自 [store.py 的 `get_or_create_collection`](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/ingestion/store.py#L22-L26)（Phase 2 同一个 `blog_chunks`）
- `.query` **不是项目里写的**，是 **Chroma 库**在 Collection 对象上的方法（和 Phase 2 的 `.upsert` 同类）
- `**kwargs` = 把 dict **展开**成 `query_embeddings=..., n_results=..., include=...` 关键字参数

Phase 2 **写库** `upsert` ↔ Phase 3 **读库** `query`。

### 5.3 拆 `raw` 与循环

Chroma 返回的 dict 外层多一层 batch（支持一次查多个问题）：

```python
ids = raw.get("ids", [[]])[0]   # 去掉外层，取第 1 个 query 的结果
```

`for chunk_id, doc, meta, dist in zip(...)` 把四条平行 list 配对，每次循环做一个 `RetrievalHit`，append 到 `hits`。

## 6. FAQ：`__init__` 到底是什么？

**`__init__` = 对象「出生」时自动执行的初始化函数**，负责把 `RetrievalHit(...)` 括号里的参数填进对象字段。

```python
hit = RetrievalHit(chunk_id="abc", content="...", metadata={...})
# 内部自动调用 __init__，执行 self.chunk_id = chunk_id 等
```

用 `@dataclass` 时 **Python 自动生成 `__init__`**，所以源码里看不到 `def __init__`，但创建对象时它仍在运行。

| 单词 | 含义 |
| --- | --- |
| `self` | 当前这个对象自己 |
| `self.chunk_id = ...` | 给这块对象的 chunk_id 赋值 |

## 7. FAQ：`mode` 什么时候变？谁改？

**容易混：有两个「默认」**

| 位置 | 默认值 | 作用 |
| --- | --- | --- |
| `types.py` `RetrievalResult.mode` | `"vector"` | dataclass 字段默认；**不会**自动切换算法 |
| `engine.py` / CLI `--mode` | `"hybrid_rerank"` | **真正决定**走哪条检索路径 |

谁改 `mode`：

```bash
python -m app.retrieval.search "..." --mode vector   # 你
python -m app.retrieval.search "..."                 # 默认 hybrid_rerank
```

[`engine.py`](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/engine.py) 根据 `mode` 调用不同函数；各函数返回时写死自己的 `mode`（如 vector_store 返回 `mode="vector"`）。

改了影响：**用哪套算法找 Top-K**、耗时、分数；**不影响**返回结构（仍是 `RetrievalResult` + K 条 `RetrievalHit`）。

## 8. FAQ：「vector」是数组吗？

**两层含义，别混：**

| 语境 | vector 指什么 |
| --- | --- |
| `q_emb`、`embedding` | **1024 个 float 的 list**（语义指纹） |
| `mode="vector"`、`vector_store.py` | **检索方式**：用向量相似度搜，不是 bm25 |

Python 里 embedding 向量就是 `list[float]`；NumPy 里常叫 array，本项目用 list 即可。

## 9. 验证

```bash
cd rag-backend && source .venv/bin/activate

python -m app.retrieval.search "什么是 RAG？" --mode vector --top-k 3
# 看 dist=、score=、[vector]、source_file

python scripts/verify_retrieval.py
```

## 10. Phase 3 带读进度

| 文件 | 状态 |
| --- | --- |
| **types.py + vector_store.py** | ✅ **本文** |
| corpus.py + bm25.py | 待读 |
| hybrid.py | 待读 |
| reranker.py + engine.py | 待读 |
| search.py + eval/ | 待读 |

## 11. 小结

**读码收获：**

1. **`vector_store.py`**：问题 embed → `collection.query` → 整理成 Top-K 条 `RetrievalHit` → `RetrievalResult`
2. **`types.py`**：K 条在 `hits` 里；`score` 越大越好，`distance` 越小越好（仅 vector）
3. **`.query` 来自 Chroma**，不是项目自写；`**kwargs` 是 dict 解包成关键字参数
4. **`__init__`** 由 `@dataclass` 自动生成，负责「填对象字段」
5. **CLI 默认 `hybrid_rerank`**，不是 types 里的 `"vector"` 默认

下一篇：**corpus.py + bm25.py** —— 不用向量，关键词怎么搜、为什么能补 vector 的短板。
