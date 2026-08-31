"""LLM Provider：DeepSeek / OpenAI 兼容接口。"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import settings

PROVIDER_REGISTRY: dict[str, dict[str, str]] = {
    "deepseek": {
        "label": "DeepSeek",
        "model": "deepseek-chat",
    },
}


def list_providers() -> list[dict[str, str]]:
    """`/models` 端点：列出可用 provider。"""
    models = []
    for name, meta in PROVIDER_REGISTRY.items():
        if name == "deepseek" and not settings.deepseek_api_key:
            continue
        models.append({"name": name, "label": meta["label"]})
    return models


def default_provider() -> str:
    providers = list_providers()
    return providers[0]["name"] if providers else "deepseek"


def _resolve_provider(provider: str) -> tuple[str, str, str]:
    """返回 (api_key, base_url, model)。"""
    if provider not in PROVIDER_REGISTRY:
        raise ValueError(f"未知 provider: {provider}")

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("未配置 DEEPSEEK_API_KEY")
        meta = PROVIDER_REGISTRY["deepseek"]
        return (
            settings.deepseek_api_key,
            settings.deepseek_base_url.rstrip("/"),
            settings.llm_model or meta["model"],
        )

    raise ValueError(f"未实现的 provider: {provider}")


async def stream_chat_completion(
    messages: list[dict[str, str]],
    *,
    provider: str = "deepseek",
) -> AsyncIterator[str]:
    """
    流式调用 chat/completions，逐 token yield 文本片段。

    使用 OpenAI 兼容 SSE：`data: {...}\n\n`
    """
    api_key, base_url, model = _resolve_provider(provider)
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,# 流式输出
        "temperature": 0.3,# 控制回答的随机性和创造性
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()# 去掉 data: 前缀
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})# 获取 delta 
                token = delta.get("content")
                if token:
                    yield token
