"""
BGE-M3 Embedding 封装：单例加载，批量向量化。

为什么用单例？
- 模型加载约 10–20s，索引多篇文章时不应重复加载
"""
from __future__ import annotations

import os
from functools import lru_cache

from app.config import settings

_PROXY_KEYS = (
    "ALL_PROXY", "all_proxy",
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
)


def _clear_proxy_for_local_model():
    if settings.embedding_is_local:
        for key in _PROXY_KEYS:
            os.environ.pop(key, None)


@lru_cache(maxsize=1)
def get_embedding_model():
    _clear_proxy_for_local_model()
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel(settings.embedding_model_path, use_fp16=False)


def embed_texts(texts: list[str], batch_size: int = 8) -> list[list[float]]:
    """批量生成 dense 向量（1024 维）。"""
    if not texts:
        return []
    model = get_embedding_model()
    output = model.encode(
        texts,
        batch_size=batch_size,
        max_length=512,
    )
    vectors = output["dense_vecs"]
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]
