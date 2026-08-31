---
layout: single
title: "RAG 学习笔记：Phase 4 state.py 带读"
date: 2026-08-31 21:50:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - LangGraph
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 4 问答后端（第一篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/graph/state.py` |
> | GitHub 原文 | [state.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/graph/state.py) |
> | 上一篇（Phase 3） | [search + eval 收官]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %}) |
> | Phase 4 系列 | **state**（本文）→ [rag_graph]({% post_url 2026-08-31-rag-phase4-rag-graph-walkthrough %}) → [prompts]({% post_url 2026-08-31-rag-phase4-prompts-walkthrough %}) → [providers]({% post_url 2026-08-31-rag-phase4-providers-walkthrough %}) |
>
> 全文 49 行。**先跟 AI 逐行读码、自己提问，再整理成博客。** Phase 3 的 `RetrievalHit` 在这里「分叉」成给 LLM 用的 hits 和给网页 Widget 用的 sources。

## 1. 读这文件之前，我已经知道什么？

[Phase 3 收官篇]({% post_url 2026-08-31-rag-retrieval-search-eval-phase3-summary %})结束时，终端 `python -m app.retrieval.search "什么是 RAG？"` 已经能打出 Top-5 hits：每条是 `RetrievalHit`，带 `content`（chunk 正文）、`metadata`（标题、文件名）、`score`（rerank 后的相关分）。

Phase 4 要做的是：**把检索结果接 LangGraph + SSE 问答**。图在节点之间要传一个「书包」——里面装什么、长什么样，就在 `state.py` 定义。

打开文件前的直觉问题：

- 既然已经有 `RetrievalHit`，为什么还要 `SourceInfo`？
- rerank 分有时是负数，前端怎么显示「71%」？
- `score = 0` 时 `hit_to_source` 没写分支，算不算 bug？

读完后的答案：**同一次检索会分成三路数据**——给 LLM 的正文、给前端的卡片、给程序判断置信度的原始分。本篇就是把这个「分叉」讲清楚。

## 2. 这文件在 Phase 4 里干什么？

| 定义 | 角色 |
| --- | --- |
| `RAGState` | LangGraph 节点之间传递的「书包」 |
| `SourceInfo` | 前端引用卡片的 schema |
| `hit_to_source` | 一条 `RetrievalHit` → 一张卡片 |
| `hits_to_sources` | 列表版转换 |

**不检索、不调 API、不拼 Prompt**——纯数据结构和格式转换。业务逻辑在 `rag_graph.py` 和 `chat.py`。

## 3. 文件头与导入（L1–L6）

```python
"""LangGraph RAG 工作流共享状态。"""
from __future__ import annotations

from typing import Any, TypedDict

from app.retrieval.types import RetrievalHit
```

- `from __future__ import annotations`：类型注解可以更灵活（习惯保留）。
- `TypedDict`：定义「像 dict 但有字段类型」的结构。
- `RetrievalHit`：Phase 3 [types 篇]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %})里的检索结果标准形态。

## 4. `SourceInfo`：前端引用卡片（L9–L15）

```python
class SourceInfo(TypedDict):
    title: str
    source_file: str
    section_title: str
    relevance_score: float
```

### TypedDict 是什么？

就是一个 dict 的 schema：

```python
# 合法
{"title": "RAG 系统基础", "source_file": "2026-08-06-RAG.md", ...}
```

运行时仍是普通 dict，但类型检查器会帮你发现缺字段。

### 为什么不用 dataclass？

SSE 要 `json.dumps(sources)` 直接序列化；TypedDict 本质是 dict，和 JSON 天然兼容。

### 「给前端」是什么意思？是 debug 日志吗？

**不是。** 「前端」= 浏览器里的博客聊天 Widget（`_includes/chat-widget.html`）。Phase 5 会把 Widget 接到后端 API；Widget 收到 `type: "sources"` 事件后渲染：

```
📚 参考来源 (5)
  #1 RAG 系统基础    71%
  #2 chunker 带读    65%
```

71% 来自 `relevance_score`（见第 6 节）。用途是让用户知道**答案引用了哪篇博客**，类似 Perplexity 的引用来源，不是给开发者 `print` 排查的日志。

## 5. `RAGState`：图里传递的书包（L18–L28）

```python
class RAGState(TypedDict, total=False):
    query: str
    provider: str
    hits: list[RetrievalHit]
    sources: list[SourceInfo]
    confidence_ok: bool
    answer: str
    retrieval_mode: str
    error: str
```

### `total=False` 什么意思？

所有字段都是**可选的**。LangGraph 节点只返回部分字段（一个 dict），框架会 **merge** 进现有 state，而不是整包替换。

### 每个字段的生命周期

| 字段 | 谁写入 | 谁读取 | 用途 |
| --- | --- | --- | --- |
| `query` | `run_rag_retrieve` 初始化 | `retrieve_node` | 用户问题 |
| `provider` | 初始化 | 预留 | 将来图内选 LLM 可用 |
| `hits` | `retrieve_node` | API 层 → `build_chat_messages` | 带正文的检索结果 |
| `sources` | `retrieve_node` | API 层 → SSE sources | 给 Widget，无正文 |
| `confidence_ok` | `retrieve_node` | 条件边 + API 层 | 要不要调 LLM |
| `answer` | retrieve（空 query）或 fallback | API 层 | 降级固定文案 |
| `retrieval_mode` | `retrieve_node` | 调试 | 如 `hybrid_rerank` |
| `error` | 预留 | 预留 | 将来图内错误处理 |

### 为什么 `hits` 和 `sources` 都要？

读码时最容易卡在这里：

| | hits | sources |
| --- | --- | --- |
| 给谁 | LLM（要读 chunk 正文） | 前端 Widget（只要标题+分数） |
| 有没有 `content` | ✅ | ❌ |
| 典型消费者 | `prompts.format_context` | SSE + `addSources()` |

**同一次检索，一份给模型读，一份给用户看。**

## 6. `hit_to_source`：原始分 → 展示分（L31–L44）

```python
def hit_to_source(hit: RetrievalHit) -> SourceInfo:
    score = hit.score
    if score < 0:
        score = max(0.0, min(1.0, 1.0 / (1.0 + abs(score))))
    elif score > 1:
        score = min(1.0, score / 10.0)
    return {
        "title": hit.post_title or hit.source_file,
        "source_file": hit.source_file,
        "section_title": hit.section_title,
        "relevance_score": round(score, 4),
    }
```

### 两种「分」别搞混（读码时的真实卡点）

| | `hit.score`（原始分） | `relevance_score`（展示分） |
| --- | --- | --- |
| 谁产生 | [reranker]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) 的 `compute_score` | 本函数换算 |
| 典型值 | `-2.3`、`-8.0`、`0.5` | `0.7055`、`0.0` |
| 用途 | 排序、`confidence_ok`（见 rag_graph 篇） | 前端显示百分比 |
| 固定 0~1？ | ❌ | ✅ 尽量映射到 0~1 |

curl 里看到的：

```json
{"title":"RAG 系统基础","relevance_score":0.7055,...}
```

就是展示分。Widget 里 `Math.round(relevance_score * 100) + "%"` → **71%**。

### 负数怎么映射？

rerank 原始分可以是负数（Cross-Encoder logits）。公式：

```
展示分 = 1.0 / (1.0 + abs(原始分))
```

| 原始分 | 展示分 |
| --- | --- |
| 0 | 1.0 |
| -1 | 0.5 |
| -5 | ~0.167 |

不是严格数学指标，只是**给人看的友好数字**。

### `score > 1` 呢？

向量/BM25/RRF 有时分数偏大，`score / 10` 再 cap 到 1.0。

### 我问 AI：`score = 0` 没写分支，怎么办？

两个 `if` 都不进（`0 < 0` 假，`0 > 1` 假），**保持 0**，`round(0, 4)` → `0.0`。不是漏写，0 已在合法展示区间。

### `round(score, 4)` 什么意思？

四舍五入到小数点后 4 位：`0.70551234` → `0.7055`。JSON 更短、界面更干净。**不影响检索排序**——排序用的是原始 `hit.score`。

### 其他字段

- `hit.post_title or hit.source_file`：标题缺失时用文件名兜底。
- `hit.post_title` / `section_title` / `source_file` 都是 `RetrievalHit` 上的 `@property`，从 `metadata` 里取。

## 7. `hits_to_sources`（L47–L48）

```python
def hits_to_sources(hits: list[RetrievalHit]) -> list[SourceInfo]:
    return [hit_to_source(h) for h in hits]
```

列表推导：5 条 hits → 5 条 sources。`retrieve_node` 里调用，结果进 `RAGState["sources"]`。

## 8. 三条数据流（本篇小结）

```
RetrievalHit（Phase 3 检索结果）
    │
    ├─ hits[].content        → prompts.py → LLM 读（用户看不见正文在 Prompt 里）
    │
    ├─ hit_to_source()       → sources → SSE → Widget 📚（用户看得见标题+百分比）
    │
    └─ hits[0].score（原始） → rag_graph confidence_ok（程序内部，用户看不见）
```

## 9. 自测题

1. 前端 sources 里有 chunk 正文吗？**没有**，正文只在 hits → Prompt 路径里。
2. `relevance_score` 和 `confidence_ok` 用的是同一个分吗？**不是**，前者展示分，后者原始 rerank 分。
3. 为什么用 TypedDict 而不是 dataclass？**SSE JSON 序列化方便，本质就是 dict。**

下一篇：[rag_graph.py]({% post_url 2026-08-31-rag-phase4-rag-graph-walkthrough %})——检索节点、置信度、条件边、`invoke` 和 merge。
