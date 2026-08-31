"""Phase 4：`/chat` SSE 与 `/models` API。"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.graph.rag_graph import run_rag_retrieve
from app.llm.prompts import FALLBACK_ANSWER, build_chat_messages
from app.llm.providers import default_provider, list_providers, stream_chat_completion

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    provider: str | None = Field(default=None, description="LLM provider，默认 deepseek")


def _sse(payload: dict) -> str:
    """SSE 行：`data: {...}\n\n`，与 chat-widget.html 解析格式一致。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


async def _chat_event_stream(query: str, provider: str) -> AsyncIterator[str]:
    yield _sse({"type": "status", "data": "检索中..."})

    try:
        state = run_rag_retrieve(query, provider=provider)
    except Exception as exc:
        yield _sse({"type": "error", "data": f"检索失败: {exc}"})
        yield _sse({"type": "done", "data": ""})
        yield _sse_done()
        return

    sources = state.get("sources") or []
    if sources:
        yield _sse({"type": "sources", "data": sources})

    if not state.get("confidence_ok"):
        answer = state.get("answer") or FALLBACK_ANSWER
        yield _sse({"type": "token", "data": answer})
        yield _sse({"type": "done", "data": ""})
        yield _sse_done()
        return

    hits = state.get("hits") or []
    messages = build_chat_messages(query, hits)

    yield _sse({"type": "status", "data": "生成中..."})

    try:
        async for token in stream_chat_completion(messages, provider=provider):
            yield _sse({"type": "token", "data": token})
    except Exception as exc:
        yield _sse({"type": "error", "data": str(exc)})
        yield _sse({"type": "done", "data": ""})
        yield _sse_done()
        return

    yield _sse({"type": "done", "data": ""})
    yield _sse_done()


@router.post("/chat")
async def chat(body: ChatRequest):
    """
    SSE 流式问答。

    事件类型：status / token / sources / done / error
    """
    provider = body.provider or default_provider()
    available = {m["name"] for m in list_providers()}
    if provider not in available:
        raise HTTPException(
            status_code=400,
            detail=f"provider 不可用: {provider}（请配置 API Key 或检查 /models）",
        )

    return StreamingResponse(
        _chat_event_stream(body.query.strip(), provider),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models")
async def models():
    """可用 LLM provider 列表。"""
    return {
        "models": list_providers(),
        "default": default_provider() if list_providers() else None,
    }
