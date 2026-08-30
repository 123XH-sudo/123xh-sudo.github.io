#!/usr/bin/env python3
"""
阶段 3 验证脚本：四种检索模式 smoke test。

运行（在 rag-backend/ 目录）：
    python scripts/verify_retrieval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.engine import search


PROBE = "什么是 RAG？"
EXPECTED = "2026-08-06-RAG.md"
MODES = ["vector", "bm25", "hybrid", "hybrid_rerank"]


def main():
    print("=" * 50)
    print("阶段 3 验证：检索模式 smoke test")
    print("=" * 50)
    print(f"探针: {PROBE}\n")

    for mode in MODES:
        result = search(PROBE, mode=mode, top_k=3)
        if not result.hits:
            print(f"❌ {mode}: 无结果")
            sys.exit(1)
        top = result.hits[0].source_file
        ok = top == EXPECTED
        mark = "✅" if ok else "⚠️ "
        print(f"{mark} {mode}: top1={top} ({result.elapsed_ms:.0f}ms)")

    print("\n✅ 阶段 3 检索 smoke test 通过")


if __name__ == "__main__":
    main()
