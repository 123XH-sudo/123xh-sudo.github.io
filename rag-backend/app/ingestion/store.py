"""
Chroma 向量库操作：collection 管理、按 source_file 增量删除、upsert。

增量更新策略（阶段 2 面试题）：
- 文章更新时，先 delete(where={"source_file": "xxx.md"}) 删掉旧 chunk
- 再 upsert 新 chunk（相同 chunk_id 会覆盖）
- 无需全量 rebuild，秒级完成单篇更新
"""
from __future__ import annotations

import chromadb

from app.config import settings
from app.ingestion.chunker import ChunkRecord


def get_client() -> chromadb.PersistentClient:
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_path))


def get_or_create_collection(client: chromadb.PersistentClient):
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def delete_by_source_file(collection, source_file: str) -> None:
    """删除某篇文章的所有旧 chunk（增量更新第一步）。"""
    try:
        existing = collection.get(where={"source_file": source_file}, include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        # collection 为空或尚无该文件时忽略
        pass


def reset_collection(client: chromadb.PersistentClient):
    """全量索引前清空 collection。"""
    try:
        client.delete_collection(settings.chroma_collection)
    except Exception:
        pass
    return get_or_create_collection(client)


def upsert_chunks(collection, chunks: list[ChunkRecord], embeddings: list[list[float]]):
    if not chunks:
        return
    collection.upsert(
        ids=[c.chunk_id for c in chunks],
        documents=[c.content for c in chunks],
        embeddings=embeddings,
        metadatas=[
            {
                "source_file": c.source_file,
                "post_title": c.post_title,
                "post_date": c.post_date,
                "post_tags": c.post_tags,
                "section_title": c.section_title,
                "char_count": c.char_count,
            }
            for c in chunks
        ],
    )


def get_collection_stats(collection) -> dict:
    return {"total_chunks": collection.count()}
