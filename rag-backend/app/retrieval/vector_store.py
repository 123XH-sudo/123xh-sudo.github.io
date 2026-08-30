"""
纯向量检索：query → BGE-M3 embed → Chroma cosine 相似度搜索。
"""
from __future__ import annotations

import time

from app.config import settings
from app.ingestion.embedder import embed_texts
from app.ingestion.store import get_client, get_or_create_collection
from app.retrieval.types import RetrievalHit, RetrievalResult


def similarity_search(
    query: str,
    top_k: int | None = None,
    *,
    source_file: str | None = None,
) -> RetrievalResult:
    if not query.strip():
        return RetrievalResult(query=query, hits=[], elapsed_ms=0.0, mode="vector")

    k = top_k if top_k is not None else settings.retrieval_top_k
    t0 = time.perf_counter()

    q_emb = embed_texts([query.strip()])[0]
    client = get_client()
    collection = get_or_create_collection(client)

    kwargs: dict = {
        "query_embeddings": [q_emb],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if source_file:
        kwargs["where"] = {"source_file": source_file}

    raw = collection.query(**kwargs)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    hits: list[RetrievalHit] = []
    ids = raw.get("ids", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
        d = float(dist)
        hits.append(
            RetrievalHit(
                chunk_id=chunk_id,
                content=doc,
                metadata=meta,
                score=1.0 - d,
                distance=d,
                rank_source="vector",
            )
        )

    return RetrievalResult(query=query, hits=hits, elapsed_ms=elapsed_ms, mode="vector")
