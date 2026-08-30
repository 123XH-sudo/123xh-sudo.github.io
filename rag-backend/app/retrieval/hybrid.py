"""
Hybrid 检索：向量 + BM25，RRF（Reciprocal Rank Fusion）融合。
"""
from __future__ import annotations

import time

from app.config import settings
from app.retrieval.bm25 import bm25_search
from app.retrieval.types import RetrievalHit, RetrievalResult
from app.retrieval.vector_store import similarity_search


def _rrf_merge(
    ranked_lists: list[list[str]],
    *,
    rrf_k: int,
    id_to_hit: dict[str, RetrievalHit],
) -> list[RetrievalHit]:
    scores: dict[str, float] = {}
    for ranks in ranked_lists:
        for rank, chunk_id in enumerate(ranks, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    hits: list[RetrievalHit] = []
    for chunk_id, score in merged:
        base = id_to_hit[chunk_id]
        hits.append(
            RetrievalHit(
                chunk_id=base.chunk_id,
                content=base.content,
                metadata=base.metadata,
                score=score,
                distance=base.distance,
                rank_source="hybrid",
            )
        )
    return hits


def hybrid_search(
    query: str,
    top_k: int | None = None,
    *,
    source_file: str | None = None,
    candidate_k: int | None = None,
) -> RetrievalResult:
    if not query.strip():
        return RetrievalResult(query=query, hits=[], elapsed_ms=0.0, mode="hybrid")

    k = top_k if top_k is not None else settings.retrieval_top_k
    fetch_k = candidate_k if candidate_k is not None else settings.retrieval_candidate_k
    fetch_k = max(fetch_k, k)

    t0 = time.perf_counter()

    vec_result = similarity_search(query, top_k=fetch_k, source_file=source_file)
    bm25_result = bm25_search(query, top_k=fetch_k, source_file=source_file)

    id_to_hit: dict[str, RetrievalHit] = {}
    for hit in vec_result.hits + bm25_result.hits:
        id_to_hit.setdefault(hit.chunk_id, hit)

    merged = _rrf_merge(
        [ [h.chunk_id for h in vec_result.hits], [h.chunk_id for h in bm25_result.hits] ],
        rrf_k=settings.hybrid_rrf_k,
        id_to_hit=id_to_hit,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return RetrievalResult(query=query, hits=merged[:k], elapsed_ms=elapsed_ms, mode="hybrid")
