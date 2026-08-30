"""从 Chroma 加载语料，供 BM25 / Hybrid 复用。"""
from __future__ import annotations

from functools import lru_cache

from app.ingestion.store import get_client, get_or_create_collection


@lru_cache(maxsize=1)
def load_corpus() -> tuple[list[str], list[str], list[dict]]:
    """
    返回 (chunk_ids, documents, metadatas)。
    进程内缓存；索引更新后需调用 invalidate_corpus_cache()。
    """
    client = get_client()
    collection = get_or_create_collection(client)
    data = collection.get(include=["documents", "metadatas"])
    return data["ids"], data["documents"], data["metadatas"]


def invalidate_corpus_cache() -> None:
    load_corpus.cache_clear()
