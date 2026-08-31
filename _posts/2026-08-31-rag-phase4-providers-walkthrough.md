---
layout: single
title: "RAG 学习笔记：Phase 4 providers.py 带读"
date: 2026-08-31 22:50:00 +0800
categories:
  - 学习笔记
tags:
  - RAG
  - Python
  - DeepSeek
  - SSE
  - 个人博客

toc: true
toc_sticky: true
---

> **对照阅读：Phase 4 问答后端（第四篇）**
>
> | | |
> | --- | --- |
> | 仓库内路径 | `rag-backend/app/llm/providers.py` |
> | GitHub 原文 | [providers.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/llm/providers.py) |
> | 上一篇 | [prompts.py]({% post_url 2026-08-31-rag-phase4-prompts-walkthrough %}) |
> | Phase 4 系列 | [state]({% post_url 2026-08-31-rag-phase4-state-walkthrough %}) → [rag_graph]({% post_url 2026-08-31-rag-phase4-rag-graph-walkthrough %}) → [prompts]({% post_url 2026-08-31-rag-phase4-prompts-walkthrough %}) → **providers**（本文） |
> | 依赖 | `.env` 里 `DEEPSEEK_API_KEY` |
>
> 全文 93 行。**先读码再写博客。** 记录 DeepSeek 流式调用、读码时 L76–92 逐行啃、以及 `temperature=0.3` 和两层 SSE 的区别。

## 1. 读这文件之前，我已经知道什么？

[prompts 篇]({% post_url 2026-08-31-rag-phase4-prompts-walkthrough %})：`build_chat_messages` 产出 `[system, user]`。

接下来要把 messages **HTTP POST 到 DeepSeek**，并且**边收边吐 token**——不能等整篇答案下完再返回（那样 SSE 打字机效果就没了）。

`providers.py` 的角色：**和 DeepSeek 说话的人**；上层 chat API 把每个 yield 出来的 token 再包一层 SSE 推给浏览器。

## 2. 在整条链路中的位置

```
build_chat_messages → messages
        ↓
stream_chat_completion(messages)     ← 本篇
        ↓ yield "根据" → yield "博客" → …
chat API async for token
        ↓
SSE {"type":"token","data":"根据"}
        ↓
Widget 打字机
```

## 3. Provider 注册表（L12–L17）

```python
PROVIDER_REGISTRY: dict[str, dict[str, str]] = {
    "deepseek": {
        "label": "DeepSeek",
        "model": "deepseek-chat",
    },
}
```

注册表模式：以后加 OpenAI、Ollama，在这里加一项 + `_resolve_provider` 分支即可。

## 4. `list_providers` 与 `default_provider`（L20–L32）

```python
def list_providers() -> list[dict[str, str]]:
    models = []
    for name, meta in PROVIDER_REGISTRY.items():
        if name == "deepseek" and not settings.deepseek_api_key:
            continue
        models.append({"name": name, "label": meta["label"]})
    return models

def default_provider() -> str:
    providers = list_providers()
    return providers[0]["name"] if providers else "deepseek"
```

- 没配 `DEEPSEEK_API_KEY` → 不列出 deepseek → chat 入口 400（provider 不可用）。
- 请求没传 `provider` → 用 `default_provider()`。

`/api/v1/models` 也调 `list_providers()`，给 Widget 下拉框用。

## 5. `_resolve_provider`（L35–L50）

```python
def _resolve_provider(provider: str) -> tuple[str, str, str]:
    """返回 (api_key, base_url, model)。"""
```

| 返回值 | 来源 | 示例 |
| --- | --- | --- |
| api_key | `.env` `DEEPSEEK_API_KEY` | `sk-...` |
| base_url | 默认 `https://api.deepseek.com/v1` | 可换代理 |
| model | `llm_model` 或 `deepseek-chat` | |

`.rstrip("/")` 防止 URL 变成 `.../v1//chat/completions`。

私有函数，只给 `stream_chat_completion` 用。

## 6. `stream_chat_completion` 签名与请求体（L53–L74）

```python
async def stream_chat_completion(
    messages: list[dict[str, str]],
    *,
    provider: str = "deepseek",
) -> AsyncIterator[str]:
```

**`async def` + `AsyncIterator[str]`** = 异步生成器；调用方：

```python
async for token in stream_chat_completion(messages):
    ...
```

### payload

```python
url = f"{base_url}/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
payload = {
    "model": model,
    "messages": messages,
    "stream": True,
    "temperature": 0.3,
}
```

| 字段 | 含义 |
| --- | --- |
| `stream: True` | 开流式；响应是 SSE 而不是一整块 JSON |
| `temperature: 0.3` | 见下一节 |
| `messages` | prompts 篇拼好的 |

## 7. `temperature=0.3` 是什么？有啥用？

**温度**控制模型每一步选词的**随机性**：

| temperature | 行为 | 适合 |
| --- | --- | --- |
| **0 ~ 0.3** | 几乎总选最 probable 的词，稳定、重复性高 | **RAG 问答** |
| 0.7 ~ 1.0 | 更多样、更有创意，易偏题 | 写作、头脑风暴 |
| > 1.0 | 很散，易胡言乱语 | 很少用 |

### 为什么 RAG 用 0.3？

1. chunk 已经塞进 Prompt，不需要模型「发挥想象」。
2. **温度低 → 更少编造**，更贴资料。
3. 同样问题多次问，答案更接近（便于调试）。

### 和其他模块的关系

```
temperature 只影响 LLM 生成
    ↓
不影响：检索、rerank、confidence_ok、sources
    ↓
confidence_ok=False 时根本不调用本函数
```

## 8. L76–92 逐行：读 DeepSeek 的 SSE（读码重点）

完整代码：

```python
async with httpx.AsyncClient(timeout=120.0) as client:
    async with client.stream("POST", url, headers=headers, json=payload) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content")
            if token:
                yield token
```

### L76：`async with httpx.AsyncClient(timeout=120.0) as client:`

- **`httpx.AsyncClient`**：异步 HTTP 客户端，适合 FastAPI 异步路由。
- **`timeout=120.0`**：最多等 120 秒；LLM 生成可能较慢。
- **`async with ... as client:`**：块结束自动关连接。

此时**还没发请求**，只是创建客户端。

### L77：`async with client.stream("POST", url, ...) as resp:`

| | `client.post()` | `client.stream()` |
| --- | --- | --- |
| 行为 | 等**整个 body** 下完 | **边收边读** |
| 适用 | 普通 JSON API | SSE 流式 |

我们设了 `stream: True`，DeepSeek 会持续推数据，**必须用 `stream()`**。

`json=payload`：httpx 自动 JSON 序列化 messages。

### L78：`resp.raise_for_status()`

| 状态码 | 行为 |
| --- | --- |
| 200 | 继续读 body |
| 401 | 抛异常（Key 错） |
| 429 | 限流 |
| 500 | 服务端错 |

异常会被上层 chat API 捕获，变成 SSE `error` 事件。

### L79：`async for line in resp.aiter_lines():`

按**行**异步读响应 body。DeepSeek 流式格式：

```
data: {"choices":[{"delta":{"content":"根据"}}]}

data: {"choices":[{"delta":{"content":"博客"}}]}

data: [DONE]

```

`aiter_lines()` 每次给一行字符串（不含 `\n`）。

### L80–L81：过滤

```python
if not line or not line.startswith("data: "):
    continue
```

空行、非 `data: ` 开头的行（注释、心跳）跳过。

### L82：`data = line[6:].strip()`

去掉 `"data: "` 前缀（6 字符）：

```
'data: {"choices":[...]}'  →  '{"choices":[...]}'
```

### L83–L84：结束标记

```python
if data == "[DONE]":
    break
```

DeepSeek 流结束；跳出循环。

### L85–L88：JSON 解析

```python
try:
    chunk = json.loads(data)
except json.JSONDecodeError:
    continue
```

解析失败跳过，不崩溃。成功后的结构示例：

```python
{
  "choices": [{
    "index": 0,
    "delta": {"content": "根据"},
    "finish_reason": None
  }]
}
```

### L89：取 delta

```python
delta = chunk.get("choices", [{}])[0].get("delta", {})
```

- `get("choices", [{}])`：没有 choices 时用 `[{}]` 防 KeyError。
- `[0]`：第一个候选。
- `get("delta", {})`：流式增量在 **delta**；非流式在 message。

第一个 chunk 可能只有 `{"role": "assistant"}`，没有 content。

### L90–L92：yield token

```python
token = delta.get("content")
if token:
    yield token
```

`None` 或 `""` 不 yield。`yield` 把 token **交给上层** `async for`。

### 模拟：3 行有效响应

| 行 | 处理 |
| --- | --- |
| `data: {"choices":[{"delta":{"role":"assistant"}}]}` | 无 content，跳过 |
| `data: {"choices":[{"delta":{"content":"根据"}}]}` | yield `"根据"` |
| `data: {"choices":[{"delta":{"content":"博客"}}]}` | yield `"博客"` |
| `data: [DONE]` | break |

上层收到 2 个 token，包装成 2 条 SSE `token` 事件。

## 9. 两层 SSE 别混（读码时的卡点）

| 层级 | 谁发 | 谁收 | 格式示例 |
| --- | --- | --- | --- |
| **内层** | DeepSeek API | providers L76–92 | `data: {"choices":[{"delta":{"content":"根据"}}]}` |
| **外层** | chat API（`app/api/chat.py`） | 浏览器 / curl | `data: {"type":"token","data":"根据"}` |

providers **只读内层、拆 token**；外层 `{type, data}` 是 chat API 的 `_sse()` 包的。

## 10. Phase 4 前半段完整串联

```
POST /api/v1/chat
    ↓
run_rag_retrieve (rag_graph)
    → hits + sources + confidence_ok
    ↓
build_chat_messages (prompts)
    → messages
    ↓
stream_chat_completion (providers)  ← 本文
    → 逐 token
    ↓
chat API → SSE → Widget
```

`app/api/chat.py` 负责 SSE 编排，消费 providers 逐 token 的 `yield`；该文件将另文带读。

## 11. 配置与验证

`.env` 示例：

```
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

有 Key 时完整流式测试：

```bash
cd rag-backend
python -m app.main
curl -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"什么是 RAG？","provider":"deepseek"}'
```

期望：status → sources → status「生成中...」→ 多个 token → done → `[DONE]`。

## 12. 自测题

1. 为什么用 `client.stream` 而不是 `post`？**stream=True 时 body 是流式来的。**
2. `yield token` 之后谁消费？**chat API 的 `async for`，再包 SSE。**
3. temperature 影响 sources 吗？**不影响，只影响 LLM 生成。**

## 13. 本篇小结

| 函数 | 作用 |
| --- | --- |
| `list_providers` | `/models`、入口校验 |
| `_resolve_provider` | 解析 Key / URL / model |
| `stream_chat_completion` | httpx 流式调 DeepSeek，yield 文本 |

Phase 4 前半段（state → rag_graph → prompts → providers）带读完结。`app/api/chat.py` 与 `main.py` 将另文续写。

