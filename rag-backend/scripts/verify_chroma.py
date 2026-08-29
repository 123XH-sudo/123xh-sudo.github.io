#!/usr/bin/env python3
"""
阶段 1 验证脚本：Chroma 持久化读写

运行（在 rag-backend/ 目录）：
    python scripts/verify_chroma.py

验证点：
1. 创建 PersistentClient，数据写入磁盘
2. add 10 条带 metadata 的文档
3. query 返回最相似结果
4. 重启 client 后数据仍在（模拟持久化）

Chroma 概念：
- Client：连接向量库的入口
- Collection：类似 SQL 的「表」，存放同一类向量
- Document：一条文本 + metadata + embedding（可自动或手动提供）
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb

from app.config import settings

COLLECTION_NAME = "phase1_verify"
TEST_DOCS = [
    ("RAG 将检索与生成结合，减少 LLM 幻觉", {"topic": "rag", "source": "test"}),
    ("向量数据库用于存储和检索 Embedding", {"topic": "vector-db", "source": "test"}),
    ("LangGraph 用图结构编排 LLM 工作流", {"topic": "langgraph", "source": "test"}),
    ("BGE-M3 是 BAAI 出品的多语言 Embedding 模型", {"topic": "embedding", "source": "test"}),
    ("FastAPI 支持 async 和 SSE 流式响应", {"topic": "fastapi", "source": "test"}),
    ("递归分块比固定长度分块更适合长文档", {"topic": "chunking", "source": "test"}),
    ("BGE-Reranker 是 Cross-Encoder，用于二次排序", {"topic": "rerank", "source": "test"}),
    ("Chroma 适合个人项目的轻量级向量存储", {"topic": "chroma", "source": "test"}),
    ("SSE 通过 text/event-stream 逐块推送数据", {"topic": "sse", "source": "test"}),
    ("个人博客 Markdown 可按标题层级分块", {"topic": "markdown", "source": "test"}),
]


def get_client() -> chromadb.PersistentClient:
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_path))


def run_verify():
    print("=" * 50)
    print("阶段 1 验证：Chroma 持久化")
    print("=" * 50)
    print(f"持久化路径: {settings.chroma_path}\n")

    client = get_client()

    # 每次验证重建 collection，避免脏数据干扰
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # 余弦相似度，RAG 常用
    )

    ids = [f"doc_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(TEST_DOCS))]
    documents = [d[0] for d in TEST_DOCS]
    metadatas = [d[1] for d in TEST_DOCS]

    # 阶段 1 用手动假向量（1024 维）验证 CRUD；阶段 2 换真实 BGE 向量
    # Chroma 要求 embedding 维度一致，这里用简单 deterministic 向量
    def fake_embed(text: str) -> list[float]:
        seed = sum(ord(c) for c in text)
        return [((seed * (i + 1)) % 1000) / 1000.0 for i in range(1024)]

    embeddings = [fake_embed(doc) for doc in documents]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    print(f"✅ 写入 {collection.count()} 条文档")

    # 查询：用第一条的 embedding 找相似项
    results = collection.query(
        query_embeddings=[embeddings[0]],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    print("\n查询「RAG 将检索与生成结合…」Top-3：")
    for i, (doc, meta, dist) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ),
        start=1,
    ):
        print(f"  #{i} distance={dist:.4f} topic={meta.get('topic')} → {doc[:30]}…")

    # 持久化验证：关闭 client，重新打开
    del client
    client2 = get_client()
    collection2 = client2.get_collection(COLLECTION_NAME)
    count_after_reopen = collection2.count()

    if count_after_reopen != len(TEST_DOCS):
        print(f"❌ 持久化失败：重启后 count={count_after_reopen}")
        sys.exit(1)

    print(f"\n✅ 持久化验证通过（重启后仍有 {count_after_reopen} 条）")
    print("✅ Chroma 验证通过")


if __name__ == "__main__":
    run_verify()
