#!/usr/bin/env python3
"""
博客知识库索引 CLI

用法（在 rag-backend/ 目录）：
    python -m app.ingestion.index --full              # 全量索引 _posts/
    python -m app.ingestion.index --file 2026-08-06-RAG.md  # 增量更新单篇
    python -m app.ingestion.index --stats             # 查看库内 chunk 数量
"""
from __future__ import annotations

import argparse
import sys

from app.config import settings
from app.ingestion.pipeline import index_all, index_file
from app.ingestion.store import get_client, get_collection_stats, get_or_create_collection


def main():
    parser = argparse.ArgumentParser(description="博客知识库索引（阶段 2）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="全量索引 _posts/ 下所有文章")
    group.add_argument("--file", metavar="NAME", help="增量索引单篇，如 2026-08-06-RAG.md")
    group.add_argument("--stats", action="store_true", help="查看 Chroma 统计信息")
    args = parser.parse_args()

    print(f"博客目录: {settings.posts_path}")
    print(f"Chroma: {settings.chroma_path} / {settings.chroma_collection}")
    print(f"Embedding: {settings.embedding_model_path}\n")

    try:
        if args.full:
            index_all()
        elif args.file:
            index_file(args.file)
        elif args.stats:
            client = get_client()
            collection = get_or_create_collection(client)
            stats = get_collection_stats(collection)
            print(f"✅ 库内 chunk 总数: {stats['total_chunks']}")
    except Exception as e:
        print(f"❌ 索引失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
