"""
Ingestion 流水线：单文件 / 全库索引。
"""
from __future__ import annotations

import time
from pathlib import Path

from app.config import settings
from app.ingestion.chunker import chunk_post
from app.ingestion.embedder import embed_texts
from app.ingestion.loader import load_post, list_posts
from app.ingestion.store import (
    delete_by_source_file,
    get_client,
    get_collection_stats,
    get_or_create_collection,
    reset_collection,
    upsert_chunks,
)


def _index_post_file(md_path: Path, collection, *, incremental: bool) -> int:
    """索引单篇文章，返回 chunk 数量。"""
    post = load_post(md_path)
    chunks = chunk_post(
        post,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    if not chunks:
        print(f"  ⚠️  无有效 chunk，跳过: {md_path.name}")
        return 0

    if incremental:
        delete_by_source_file(collection, post.source_file)

    texts = [c.content for c in chunks]
    embeddings = embed_texts(texts)
    upsert_chunks(collection, chunks, embeddings)
    return len(chunks)


def index_file(filename: str) -> dict:
    """增量索引单篇博客（--file）。"""
    md_path = settings.posts_path / filename
    if not md_path.exists():
        raise FileNotFoundError(f"文章不存在: {md_path}")

    t0 = time.perf_counter()
    client = get_client()
    collection = get_or_create_collection(client)

    print(f"📄 增量索引: {filename}")
    n = _index_post_file(md_path, collection, incremental=True)
    elapsed = time.perf_counter() - t0
    stats = get_collection_stats(collection)

    print(f"  └─ 写入 {n} 个 chunk，耗时 {elapsed:.1f}s")
    print(f"✅ 库内总计 {stats['total_chunks']} 个 chunk")
    return {"file": filename, "chunks": n, "elapsed_s": round(elapsed, 2), **stats}


def index_all() -> dict:
    """全量索引 _posts/ 下所有文章（--full）。"""
    posts_dir = settings.posts_path
    if not posts_dir.is_dir():
        raise FileNotFoundError(f"博客目录不存在: {posts_dir}")

    files = list_posts(posts_dir)
    if not files:
        raise RuntimeError(f"未找到 Markdown 文件: {posts_dir}")

    t0 = time.perf_counter()
    client = get_client()
    collection = reset_collection(client)

    total_chunks = 0
    for md_path in files:
        print(f"📄 处理: {md_path.name}")
        n = _index_post_file(md_path, collection, incremental=False)
        total_chunks += n
        print(f"  └─ {n} 个 chunk")

    elapsed = time.perf_counter() - t0
    stats = get_collection_stats(collection)

    print(f"\n✅ 全量索引完成: {len(files)} 篇文章, {total_chunks} 个 chunk, 耗时 {elapsed:.1f}s")
    return {
        "files": len(files),
        "chunks": total_chunks,
        "elapsed_s": round(elapsed, 2),
        **stats,
    }
