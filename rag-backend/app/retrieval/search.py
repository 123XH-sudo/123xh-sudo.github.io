#!/usr/bin/env python3
"""
检索 CLI（阶段 3）

用法（在 rag-backend/ 目录）：
    python -m app.retrieval.search "什么是 RAG？"
    python -m app.retrieval.search "Docker 部署" --mode hybrid --top-k 3
    python -m app.retrieval.search "incremental" --mode bm25
    python -m app.retrieval.search "分块策略" --file 2026-08-29-rag-ingestion-chunker-walkthrough.md
"""
from __future__ import annotations

import argparse
import sys

from app.config import settings
from app.retrieval.engine import search


def main():
    parser = argparse.ArgumentParser(description="博客知识库检索（阶段 3）")
    parser.add_argument("query", help="检索问题")
    parser.add_argument(
        "--mode",
        choices=["vector", "bm25", "hybrid", "hybrid_rerank"],
        default="hybrid_rerank",
        help="检索模式（默认 hybrid_rerank）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=settings.retrieval_top_k,
        help=f"返回条数（默认 {settings.retrieval_top_k}）",
    )
    parser.add_argument(
        "--file",
        metavar="NAME",
        help="仅在指定文章内检索",
    )
    args = parser.parse_args()

    print(f"Chroma: {settings.chroma_path} / {settings.chroma_collection}")
    print(f"模式: {args.mode}")
    if args.file:
        print(f"范围: {args.file}")
    print(f"Query: {args.query}\n")

    try:
        result = search(
            args.query,
            mode=args.mode,
            top_k=args.top_k,
            source_file=args.file,
        )
    except Exception as e:
        print(f"❌ 检索失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not result.hits:
        print("未找到相关 chunk")
        sys.exit(0)

    for i, hit in enumerate(result.hits, start=1):
        score_label = f"score={hit.score:.4f}"
        if hit.distance is not None:
            score_label += f" dist={hit.distance:.4f}"
        print(f"#{i} {score_label} [{hit.rank_source}] {hit.source_file}")
        print(f"   【{hit.post_title} > {hit.section_title}】")
        preview = hit.content.replace("\n", " ")[:120]
        print(f"   {preview}…\n")

    print(f"✅ {len(result.hits)} 条结果, 耗时 {result.elapsed_ms:.0f}ms")


if __name__ == "__main__":
    main()
