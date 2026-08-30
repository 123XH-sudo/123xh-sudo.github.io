"""
BGE-Reranker 二次排序：Cross-Encoder，对 Hybrid 候选集精排。
"""
from __future__ import annotations

import os
import time
from functools import lru_cache

from app.config import settings
from app.retrieval.types import RetrievalHit, RetrievalResult

_PROXY_KEYS = (
    "ALL_PROXY", "all_proxy",
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
)


def _clear_proxy_for_local_model():
    if settings.reranker_is_local:
        for key in _PROXY_KEYS:
            os.environ.pop(key, None)


@lru_cache(maxsize=1)
def get_reranker_model():
    _clear_proxy_for_local_model()
    from FlagEmbedding import FlagReranker

    return FlagReranker(settings.reranker_model_path, use_fp16=False)


def rerank_hits(
    query: str,
    hits: list[RetrievalHit],
    top_k: int | None = None,
) -> list[RetrievalHit]:
    """对候选 hits 按 Cross-Encoder 分数重排，返回 top_k。"""
    if not hits:
        return []

    k = top_k if top_k is not None else settings.retrieval_top_k
    model = get_reranker_model()
    pairs = [[query.strip(), h.content] for h in hits]
    scores = model.compute_score(
        pairs,
        batch_size=settings.rerank_batch_size,
        max_length=512,
    )

    if not isinstance(scores, list):
        scores = [scores]

    scored = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)
    result: list[RetrievalHit] = []
    for hit, score in scored[:k]:
        result.append(
            RetrievalHit(
                chunk_id=hit.chunk_id,
                content=hit.content,
                metadata=hit.metadata,
                score=float(score),
                distance=hit.distance,
                rank_source="rerank",
            )
        )
    return result


def rerank_search(
    query: str,
    candidates: list[RetrievalHit],
    top_k: int | None = None,
) -> RetrievalResult:
    t0 = time.perf_counter()
    hits = rerank_hits(query, candidates, top_k=top_k)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return RetrievalResult(query=query, hits=hits, elapsed_ms=elapsed_ms, mode="rerank")
