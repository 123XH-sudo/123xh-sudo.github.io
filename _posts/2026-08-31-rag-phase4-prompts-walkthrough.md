---
layout: single
title: "RAG 学习笔记：Phase 4 prompts.py 带读"
date: 2026-08-31 22:30:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - Prompt
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 4 问答后端（第三篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/llm/prompts.py` |
> | GitHub 原文 | [prompts.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/llm/prompts.py) |
> | 上一篇 | [rag_graph.py]({% post_url 2026-08-31-rag-phase4-rag-graph-walkthrough %}) |
> | Phase 4 系列 | [state]({% post_url 2026-08-31-rag-phase4-state-walkthrough %}) → [rag_graph]({% post_url 2026-08-31-rag-phase4-rag-graph-walkthrough %}) → **prompts**（本文）→ [providers]({% post_url 2026-08-31-rag-phase4-providers-walkthrough %}) |
>
> 全文 43 行。**纯字符串组装，无 IO。** `confidence_ok=True` 时，API 层调用 `build_chat_messages(query, hits)`，产出 DeepSeek 需要的 `messages` 数组。

## 1. 读这文件之前，我已经知道什么？

[rag_graph 篇]({% post_url 2026-08-31-rag-phase4-rag-graph-walkthrough %})：`confidence_ok=True` 时图返回 5 条 `hits`（带 chunk 正文），但不生成答案。

接下来要问 LLM，不能只有「什么是 RAG？」——必须把**检索到的段落**塞进请求里。这就是 RAG 和普通聊天的分水岭。

| | 普通 ChatGPT | 本项目 RAG |
| --- | --- | --- |
| 输入 | 用户问题 | **参考资料 + 用户问题** |
| 知识从哪来 | 训练记忆 | 博客 chunk（Phase 2 索引） |
| 防编造 | 靠模型自觉 | `SYSTEM_PROMPT` 硬约束 |

`prompts.py` **不检索、不调 API**，只做字符串组装。是 Phase 4 里最好单测、最好读的一文件。

## 2. 在整条链路中的位置

```
run_rag_retrieve → hits (5条, 带 content)
        ↓
build_chat_messages(query, hits)   ← 本篇
        ↓
[system, user] messages
        ↓
stream_chat_completion (providers 篇)
        ↓
DeepSeek 流式回答
```

[sources 事件]({% post_url 2026-08-31-rag-phase4-state-walkthrough %})里的标题和百分比**不会**进 Prompt；进 Prompt 的是 `hit.content` 全文。

## 3. 文件头与导入（L1–L4）

```python
"""RAG Prompt 模板。"""
from __future__ import annotations

from app.retrieval.types import RetrievalHit
```

只依赖 `RetrievalHit` 的：

- `post_title` / `section_title` / `source_file`（property，来自 metadata）
- `content`（chunk 正文）

## 4. `SYSTEM_PROMPT`：岗位说明书（L6–L11）

```python
SYSTEM_PROMPT = """你是个人博客「123XH-sudo」的问答助手。
规则：
1. 仅根据用户提供的「参考资料」回答，不要编造资料中没有的内容。
2. 若参考资料不足以回答问题，请明确说明「根据博客现有内容无法确定」，不要猜测。
3. 使用与用户问题相同的语言（中文优先）。
4. 回答简洁清晰，可适度使用 Markdown。"""
```

### 四条规则分别防什么

| 规则 | 防什么 | curl 答案里的体现 |
| --- | --- | --- |
| 1. 仅根据参考资料 | **幻觉** | 「根据博客内容，RAG 是…」 |
| 2. 不够就说无法确定 | **硬猜** | 资料缺时会明说 |
| 3. 同语言 | 中文问英文答 | 中文问 → 中文答 |
| 4. 简洁 + Markdown | 排版 | 列表、加粗 |

### 为什么是 system 角色？

OpenAI / DeepSeek 的 chat 格式里，**system** 放「永久规则」，**user** 放「本次对话内容」。system 用户一般看不见，但强约束模型行为。

### 为什么写成模块级常量？

方便改文案、写测试、博客引用；一处修改全局生效。

## 5. `format_context`：hits → 参考资料文本（L14–L23）

### L16–L17：空列表兜底

```python
if not hits:
    return "（无参考资料）"
```

正常 LLM 分支 hits 非空；防御性代码。若真为空，配合 system 规则 2，模型应说「无法确定」。

### L19–L22：逐条拼 block

```python
blocks: list[str] = []
for i, hit in enumerate(hits, start=1):
    header = f"[{i}] {hit.post_title} > {hit.section_title} ({hit.source_file})"
    blocks.append(f"{header}\n{hit.content.strip()}")
```

**`enumerate(hits, start=1)`**  
编号从 1 开始：`[1]`、`[2]`… LLM 可引用「见 [1]」。

**header 一行元信息：**

```
[1] RAG 系统基础 > 1. 什么是RAG? (2026-08-06-RAG.md)
```

**`hit.content.strip()`**  
chunk 正文，RAG 的核心燃料。通常几百字，来自 Phase 2 分块。

### L23：块之间分隔

```python
return "\n\n---\n\n".join(blocks)
```

5 条 hits 拼成一大段，视觉上：

```
[1] RAG 系统基础 > 1. 什么是RAG? (2026-08-06-RAG.md)
RAG 是检索增强生成（Retrieval-Augmented Generation）……

---

[2] chunker 带读 > 什么是 RAG (2026-08-06-chunker-walkthrough.md)
……
```

`\n\n---\n\n` 让模型容易区分「第 1 段 / 第 2 段」。

## 6. `build_chat_messages`：OpenAI 兼容格式（L26–L36）

### 拼 user 内容

```python
context = format_context(hits)
user_content = f"""参考资料：
{context}

用户问题：{query}"""
```

结构固定：

```
参考资料：
（5 段 chunk 全文）

用户问题：什么是 RAG？
```

### 返回 messages 数组

```python
return [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_content},
]
```

DeepSeek `/chat/completions` 直接吃这个结构：

```python
payload = {"model": "...", "messages": messages, "stream": True, ...}
```

### 为什么参考资料放在 user 里而不是 system？

常见 RAG 拼法：

| 角色 | 放什么 | 换问题时要不要改 |
| --- | --- | --- |
| system | 永久规则 | 不改 |
| user | 动态上下文 + 问题 | **每次改** |

换问题只改 `user_content`，`SYSTEM_PROMPT` 不变。

### 和 sources 的再次对照

| 内容 | sources（SSE） | Prompt（user） |
| --- | --- | --- |
| 标题 | ✅ | ✅ header 里 |
| relevance_score | ✅ | ❌ |
| content 正文 | ❌ | ✅ 必须有 |

用户在前端看到「#1 RAG 系统基础 71%」，LLM 在背后读的是该条对应的**整段 markdown 正文**。

## 7. `FALLBACK_ANSWER`（L39–L42）

```python
FALLBACK_ANSWER = (
    "抱歉，我在博客知识库中没有找到足够相关的内容来回答这个问题。"
    "你可以换个问法，或确认该主题是否已在博客文章中写过。"
)
```

### 三处引用

| 位置 | 何时 |
| --- | --- |
| `retrieve_node` | 空 query |
| `fallback_node` | `confidence_ok=False` |
| chat API | `state.get("answer") or FALLBACK_ANSWER` 兜底 |

### 和 `SYSTEM_PROMPT` 的区别

| | FALLBACK_ANSWER | SYSTEM_PROMPT |
| --- | --- | --- |
| 谁输出 | 后端直接推给用户 | 给 LLM 看的规则 |
| 调 LLM？ | ❌ | ✅（LLM 分支） |
| 内容 | 固定字符串 | 约束生成行为 |

放在 `prompts.py` 是因为**文案集中管理**；虽然 fallback 不经过 LLM，但和「对用户说什么」同类。

## 8. 走一遍：「什么是 RAG？」

```
1. hits = 5 条，Top-1 来自 2026-08-06-RAG.md
2. format_context → 约几千字「参考资料」
3. build_chat_messages("什么是 RAG？", hits)
4. messages = [
     {role: system, content: "你是个人博客…"},
     {role: user, content: "参考资料：\n[1] RAG 系统基础…\n\n用户问题：什么是 RAG？"},
   ]
5. 交给 providers.stream_chat_completion
```

LLM **看不到** `relevance_score`；它只读正文和规则。

## 9. 自测题

1. Prompt 里有没有 sources 的百分比？**没有。**
2. 换模型（DeepSeek → 其他 OpenAI 兼容）要改 prompts 吗？**一般不用**，messages 格式通用。
3. 能否把参考资料也塞 system？**可以但不常见**；动态内容放 user 是惯例。

## 10. 本篇小结

```
confidence_ok=True
    → build_chat_messages(query, hits)
    → [system, user]
    → providers.py
```

下一篇：[providers.py]({% post_url 2026-08-31-rag-phase4-providers-walkthrough %})——httpx 流式、temperature、L76–92 逐行、两层 SSE。
