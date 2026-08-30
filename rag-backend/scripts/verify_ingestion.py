#!/usr/bin/env python3
"""
阶段 2 验证脚本：ingestion 流水线 + Chroma 数据质量 + 检索探针

运行（在 rag-backend/ 目录）：
    python scripts/verify_ingestion.py

验证点：
1. blog_chunks collection 存在且 chunk > 0
2. metadata 六字段齐全，embedding 1024 维，正文含标题前缀
3. _posts/ 文章数与已索引 source_file 一致
4. where source_file 过滤可用
5. 检索探针：问题 embed 后能 query 出相关 chunk
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.ingestion.embedder import embed_texts
from app.ingestion.loader import list_posts
from app.ingestion.store import get_client, get_or_create_collection

REQUIRED_METADATA = {
    "source_file",
    "post_title",
    "post_date",
    "post_tags",
    "section_title",
    "char_count",
}
EXPECTED_EMBED_DIM = 1024
PROBE_QUERY = "什么是 RAG 检索增强生成？"


def _fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"✅ {msg}")


def run_verify() -> dict:
    print("=" * 50)
    print("阶段 2 验证：Ingestion + Chroma 数据质量")
    print("=" * 50)
    print(f"博客目录: {settings.posts_path}")
    print(f"Chroma: {settings.chroma_path} / {settings.chroma_collection}\n")

    client = get_client()
    col = get_or_create_collection(client)
    total = col.count()
    if total <= 0:
        _fail(f"collection 为空，请先运行 python -m app.ingestion.index --full")

    _ok(f"库内 chunk 总数: {total}")

    sample = col.get(limit=1, include=["metadatas", "documents", "embeddings"])
    meta = sample["metadatas"][0]
    doc = sample["documents"][0]
    emb = sample["embeddings"][0]

    missing = REQUIRED_METADATA - set(meta.keys())
    if missing:
        _fail(f"metadata 缺字段: {missing}")
    _ok(f"metadata 六字段齐全: {sorted(REQUIRED_METADATA)}")

    if len(emb) != EXPECTED_EMBED_DIM:
        _fail(f"embedding 维度期望 {EXPECTED_EMBED_DIM}，实际 {len(emb)}")
    _ok(f"embedding 维度: {len(emb)}")

    if not doc.startswith("【"):
        _fail("chunk 正文缺少「【标题 > 章节】」前缀")
    _ok("chunk 含标题前缀")

    posts = list_posts(settings.posts_path)
    expected_files = {p.name for p in posts}
    indexed_files = {m["source_file"] for m in col.get(include=["metadatas"])["metadatas"]}
    missing_posts = expected_files - indexed_files
    extra_posts = indexed_files - expected_files

    _ok(f"_posts/ 文章数: {len(expected_files)}，已索引: {len(indexed_files)}")
    if missing_posts:
        print(f"⚠️  未索引文章 ({len(missing_posts)}):")
        for name in sorted(missing_posts):
            print(f"     - {name}")
    if extra_posts:
        print(f"⚠️  库内多余 source_file ({len(extra_posts)}): {sorted(extra_posts)}")

    sf = meta["source_file"]
    n_filtered = len(col.get(where={"source_file": sf}, include=[])["ids"])
    if n_filtered <= 0:
        _fail(f"where source_file={sf!r} 无结果")
    _ok(f"metadata 过滤可用（{sf} → {n_filtered} chunks）")

    print("\n--- 检索探针 ---")
    q_emb = embed_texts([PROBE_QUERY])[0]
    if len(q_emb) != EXPECTED_EMBED_DIM:
        _fail(f"query embedding 维度异常: {len(q_emb)}")

    res = col.query(
        query_embeddings=[q_emb],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )
    hits = res["documents"][0]
    if not hits:
        _fail("检索探针无结果")

    for i, (hit_doc, hit_meta, dist) in enumerate(
        zip(hits, res["metadatas"][0], res["distances"][0]), start=1
    ):
        print(f"  #{i} dist={dist:.4f} file={hit_meta['source_file']}")
        print(f"      {hit_doc[:72]}…")

    top_file = res["metadatas"][0][0]["source_file"]
    _ok(f"检索探针 Top-1: {top_file}")

    print("\n" + "=" * 50)
    if missing_posts:
        print("⚠️  部分文章未索引，请运行:")
        for name in sorted(missing_posts):
            print(f"    python -m app.ingestion.index --file {name}")
        print("或: python -m app.ingestion.index --full")
        sys.exit(1)

    print("✅ 阶段 2 Ingestion 验证通过")
    return {
        "total_chunks": total,
        "articles": len(indexed_files),
        "probe_top1": top_file,
    }


if __name__ == "__main__":
    run_verify()
