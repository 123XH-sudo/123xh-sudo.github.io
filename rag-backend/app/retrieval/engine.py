"""
统一检索入口：vector / bm25 / hybrid / hybrid_rerank。
"""
from __future__ import annotations

import time
from typing import Literal

from app.config import settings
from app.retrieval.bm25 import bm25_search
from app.retrieval.hybrid import hybrid_search
from app.retrieval.reranker import rerank_hits
from app.retrieval.types import RetrievalResult
from app.retrieval.vector_store import similarity_search

SearchMode = Literal["vector", "bm25", "hybrid", "hybrid_rerank"]


def search(
    query: str,
    mode: SearchMode = "hybrid_rerank",
    top_k: int | None = None,
    *,
    source_file: str | None = None,
) -> RetrievalResult:
    k = top_k if top_k is not None else settings.retrieval_top_k

    if mode == "vector":
        return similarity_search(query, top_k=k, source_file=source_file)

    if mode == "bm25":
        return bm25_search(query, top_k=k, source_file=source_file)

    if mode == "hybrid":
        return hybrid_search(query, top_k=k, source_file=source_file)

    if mode == "hybrid_rerank":
        t0 = time.perf_counter()
        hybrid_result = hybrid_search(
            query,
            top_k=settings.retrieval_candidate_k,
            source_file=source_file,
        )
        reranked = rerank_hits(query, hybrid_result.hits, top_k=k)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return RetrievalResult(
            query=query,
            hits=reranked,
            elapsed_ms=elapsed_ms,
            mode="hybrid_rerank",
        )

    raise ValueError(f"未知检索模式: {mode}")
