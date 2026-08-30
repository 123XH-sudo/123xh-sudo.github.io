"""
BM25 关键词检索：基于 rank_bm25，适合专有名词 / 英文术语精确匹配。
"""
from __future__ import annotations

import re
import time
from functools import lru_cache

from rank_bm25 import BM25Okapi

from app.config import settings
from app.retrieval.corpus import load_corpus
from app.retrieval.types import RetrievalHit, RetrievalResult

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    """中英文混合分词：中文单字 + 英文单词。"""
    text = text.lower()
    return _TOKEN_RE.findall(text)


@lru_cache(maxsize=1)
def _get_bm25_index() -> tuple[BM25Okapi, list[str], list[str], list[dict]]:
    ids, documents, metadatas = load_corpus()
    tokenized = [tokenize(doc) for doc in documents]
    return BM25Okapi(tokenized), ids, documents, metadatas


def invalidate_bm25_cache() -> None:
    _get_bm25_index.cache_clear()


def bm25_search(
    query: str,
    top_k: int | None = None,
    *,
    source_file: str | None = None,
) -> RetrievalResult:
    if not query.strip():
        return RetrievalResult(query=query, hits=[], elapsed_ms=0.0, mode="bm25")

    k = top_k if top_k is not None else settings.retrieval_top_k
    t0 = time.perf_counter()

    bm25, ids, documents, metadatas = _get_bm25_index()
    query_tokens = tokenize(query.strip())

    if source_file:
        indices = [i for i, m in enumerate(metadatas) if m.get("source_file") == source_file]
        if not indices:
            return RetrievalResult(
                query=query, hits=[], elapsed_ms=(time.perf_counter() - t0) * 1000, mode="bm25"
            )
        scores = bm25.get_batch_scores(query_tokens, indices)
        ranked = sorted(zip(indices, scores), key=lambda x: x[1], reverse=True)[:k]
    else:
        scores = bm25.get_scores(query_tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]

    hits: list[RetrievalHit] = []
    for idx, score in ranked:
        if score <= 0:
            continue
        hits.append(
            RetrievalHit(
                chunk_id=ids[idx],
                content=documents[idx],
                metadata=metadatas[idx],
                score=float(score),
                rank_source="bm25",
            )
        )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return RetrievalResult(query=query, hits=hits, elapsed_ms=elapsed_ms, mode="bm25")
