---
layout: single
title: "RAG 学习笔记：Phase 4 rag_graph.py 带读"
date: 2026-08-31 22:10:00 +0800
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

> **对照阅读：Phase 4 问答后端（第二篇）**
>
>
> |            |                                                                                                                                                                                                                                    |
> | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
> | 仓库内路径      | `rag-backend/app/graph/rag_graph.py`                                                                                                                                                                                               |
> | GitHub 原文  | [rag_graph.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/graph/rag_graph.py)                                                                                                                    |
> | 上一篇        | [state.py]({% post_url 2026-08-31-rag-phase4-state-walkthrough %})                                                                                                                                                                 |
> | Phase 4 系列 | [state]({% post_url 2026-08-31-rag-phase4-state-walkthrough %}) → **rag_graph**（本文）→ [prompts]({% post_url 2026-08-31-rag-phase4-prompts-walkthrough %}) → [providers]({% post_url 2026-08-31-rag-phase4-providers-walkthrough %}) |
> | 验证         | `python scripts/verify_chat.py`                                                                                                                                                                                                    |
>
>
> 全文 82 行。**先读码再写博客。** 记录 LangGraph 怎么接 Phase 3 检索、置信度判断、以及读码时把「图」和「流式 LLM」搞混的纠错。



## 1. 读这文件之前，我已经知道什么？

- [state 篇]({% post_url 2026-08-31-rag-phase4-state-walkthrough %})：`RAGState`、`hits` vs `sources`、两种分的区别。
- 阶段 1 `hello_graph.py`：`StateGraph`、节点返回部分 dict、`.invoke(initial)`。
- Phase 3：`engine.search(..., mode="hybrid_rerank")` 已是默认最强检索。

Phase 4 的核心问题变成：**检索完之后，要不要调 LLM？图负责到哪一步？**

## 2. 整体架构：图管什么、API 管什么

文件头注释写得很关键：

> 图负责检索与降级分支；LLM 流式生成在 /chat SSE 中调用，便于逐 token 推送。

```
┌─────────────────────────────────────────┐
│  chat API（`app/api/chat.py`，后续篇章）   │
│  SSE：status → sources → token → done   │
└─────────────────┬───────────────────────┘
                  │ run_rag_retrieve()
                  ▼
┌─────────────────────────────────────────┐
│  rag_graph（本篇）                        │
│  retrieve → confidence_ok? → fallback?  │
└─────────────────────────────────────────┘
```

**为什么 generate 不在图里？** LangGraph 的 `invoke()` 是**跑完整张图、一次性返回**。浏览器要的 SSE 是**边生成边推 token**。所以图只做到「检索 + 判断 + 写 fallback 文案」；流式 LLM 必须在 API 层。

---

## 3. 和 hello_graph 对照


|          | hello_graph                        | rag_graph                  |
| -------- | ---------------------------------- | -------------------------- |
| 节点       | receive → transform → generate（线性） | retrieve → 条件分叉 → fallback |
| generate | 在图里写 `final_answer`                | **不在图里**                   |
| 输出       | JSON 一次返回                          | 图返回 state，API 推 SSE        |
| 业务       | 字符串 `.upper()` 玩具                  | 真 `engine.search`          |


阶段 1 注释里写过：「后续可加检索置信度低 → 走降级分支」——Phase 4 就在 `add_conditional_edges` 这里实现。

## 4. 导入（L6–L13）

```python
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph.state import RAGState, hits_to_sources
from app.llm.prompts import FALLBACK_ANSWER
from app.retrieval.engine import search
```


| 导入                | 作用                                           |
| ----------------- | -------------------------------------------- |
| `END, START`      | LangGraph 虚拟起止节点                             |
| `settings`        | `retrieval_top_k`、`retrieval_confidence_min` |
| `hits_to_sources` | hits → 前端 sources                            |
| `FALLBACK_ANSWER` | 固定道歉文案                                       |
| `search`          | Phase 3 统一检索入口                               |




## 5. `retrieve_node` 逐行（L16–L39）



### 节点函数约定

```python
def retrieve_node(state: RAGState) -> dict:
```

和 hello_graph 一样：**输入完整 state，输出只含要更新的字段**，LangGraph 负责 merge。

### L18–L26：空 query 短路

```python
query = state.get("query", "").strip()
if not query:
    return {
        "hits": [], "sources": [], "confidence_ok": False,
        "answer": FALLBACK_ANSWER, "retrieval_mode": "none",
    }
```

API 层 Pydantic 已要求 `query` 至少 1 字符；这里是防御性代码。不调 `search`，省时间。

### L28：一行复用 Phase 3

```python
result = search(query, mode="hybrid_rerank", top_k=settings.retrieval_top_k)
```

[engine.py]({% post_url 2026-08-31-rag-retrieval-reranker-engine-walkthrough %}) 里 `hybrid_rerank` 的流程：

```
hybrid_search(top_k=15 候选) → rerank_hits(top_k=5) → RetrievalResult
```

rag_graph **没有重写检索**。

### L29–L30：hits 与 sources

```python
hits = result.hits
sources = hits_to_sources(hits)
```

- `hits`：带 `content`，后面给 Prompt。
- `sources`：给 SSE，Widget 显示 📚。



### L32：置信度（读码重点）

```python
confidence_ok = bool(hits) and hits[0].score >= settings.retrieval_confidence_min
```

两个条件**同时**满足（`and`）：

1. `bool(hits)` — 至少有一条结果。
2. `hits[0].score >= retrieval_confidence_min` — **Top-1 的 rerank 原始分**不能太低。

**注意：** 这里用的是 [state 篇]({% post_url 2026-08-31-rag-phase4-state-walkthrough %})里的 **原始分**，不是前端的 `relevance_score`。

### 默认阈值 `-5.0` 从哪来？

写在 `config.py`：

```python
retrieval_confidence_min: float = -5.0
```

**不是 reranker 或 LangGraph 内置常数**，是我们项目第一版的工程默认值。rerank 分常为负数，-5 偏宽松，正常博客问题 Top-1 通常能过。后续优化方向：

- 用 `eval/run_eval.py` 看 fallback 误杀/漏杀率；
- 改 `.env` 的 `RETRIEVAL_CONFIDENCE_MIN`；
- 加 Top-1 与 Top-2 分差等条件。



### L34–L39：正常返回

```python
return {
    "hits": hits, "sources": sources,
    "confidence_ok": confidence_ok,
    "retrieval_mode": result.mode,
}
```

**没有写** `answer`——要走 LLM 时 answer 留空，由 API 层流式填充。

## 6. `fallback_node`（L42–L44）

```python
def fallback_node(state: RAGState) -> dict:
    return {"answer": FALLBACK_ANSWER}
```

只做一件事：写入固定道歉。**不调 LLM** → 不花钱、不幻觉。

## 7. `route_after_retrieve` 与条件边（L47–L66）



### 路由函数

```python
def route_after_retrieve(state: RAGState) -> str:
    if state.get("confidence_ok"):
        return "ok"
    return "fallback"
```

返回值必须是字符串，且和下面 dict 的 key **完全一致**。

### 建图

```python
graph = StateGraph(RAGState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("fallback", fallback_node)

graph.add_edge(START, "retrieve")
graph.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {"ok": END, "fallback": "fallback"},
)
graph.add_edge("fallback", END)
return graph.compile()
```

流程图：

```
START → retrieve → route_after_retrieve
                      ├─ "ok"       → END
                      └─ "fallback" → fallback → END
```

`"ok"` 指向 `END` 不是漏写节点——意思是**图结束**，把 merge 后的 state 交还给 API 层。

### `add_conditional_edges` 三个参数

1. 从哪个节点出来：`"retrieve"`
2. 调哪个函数决定方向：`route_after_retrieve`
3. 返回值 → 下一跳：`{"ok": END, "fallback": "fallback"}`



## 8. `run_rag_retrieve` 与 `invoke`（L69–L81）

```python
def run_rag_retrieve(query: str, provider: str = "deepseek") -> RAGState:
    app = build_rag_graph()
    initial: RAGState = { ... }
    return app.invoke(initial)
```



### `invoke` 是什么？

LangGraph 提供的**跑图**方法：

```
输入 initial → START → ... → END → 返回 merge 后的完整 RAGState
```

**同步阻塞**：检索 + rerank 期间，客户端只能等着（API 层会先推「检索中...」）。

### merge 是什么？

每个节点只返回部分字段，LangGraph **叠到 initial 上**，没提到的字段保留原值。

**例子：**`confidence_ok=True`**（「什么是 RAG？」）**

```python
# initial 片段
{"query": "什么是 RAG？", "hits": [], "confidence_ok": False, "answer": ""}

# retrieve_node 返回后 merge
{
  "query": "什么是 RAG？",
  "hits": [5条 RetrievalHit],
  "sources": [5条 SourceInfo],
  "confidence_ok": True,
  "answer": "",                    # 仍为空
  "retrieval_mode": "hybrid_rerank",
}
```

route → `"ok"` → END，不经过 fallback。

**例子：乱问「火星天气」**

```python
# merge 后
{"confidence_ok": False, "answer": "抱歉，我在博客知识库中..."}
```



### `provider` 传进 initial 但图里没用？

对，retrieve/fallback 都不读；预留给将来图内选 LLM。现在 LLM 在 API 层用同一个 provider。

## 9. 置信度与 True/False：我读码时的理解过程

一开始以为 `confidence_ok` 是 0/1 数字——其实是 Python `True`**/**`False`，逻辑一样：


| `confidence_ok` | 图做什么                | API 层做什么               |
| --------------- | ------------------- | ---------------------- |
| `False`         | fallback 写 `answer` | 不调 LLM，把道歉当 token 推出   |
| `True`          | 不写 answer，END       | 拼 Prompt → 流式 DeepSeek |


**置信度在判断什么？** 知识库检索是否够靠谱，值得调 LLM。不是 LLM 自不自信，是**检索质量门槛**。

## 10. 走一遍：「什么是 RAG？」

```
1. run_rag_retrieve("什么是 RAG？")
2. retrieve: search(hybrid_rerank) → 5 hits, 5 sources
3. hits[0].score ≈ -2.x >= -5.0 → confidence_ok=True
4. route → "ok" → END
5. 返回 state 给 API：sources + hits + confidence_ok=True
6. API 推 sources → build_chat_messages → stream LLM（providers 篇）
```



## 11. 验证

```bash
cd rag-backend
python scripts/verify_chat.py
```

期望：Top-1 为 `2026-08-06-RAG.md`，`confidence_ok=True`。

## 12. 本篇小结


| 函数                     | 角色                           |
| ---------------------- | ---------------------------- |
| `retrieve_node`        | Phase 3 检索 + `confidence_ok` |
| `fallback_node`        | 固定道歉                         |
| `route_after_retrieve` | 分叉 ok / fallback             |
| `build_rag_graph`      | 拼 LangGraph                  |
| `run_rag_retrieve`     | 对外入口                         |


**图管「搜不搜、信不信」；流式管「怎么说」。**

下一篇：[prompts.py]({% post_url 2026-08-31-rag-phase4-prompts-walkthrough %})——chunk 正文怎么拼进 Prompt。