#!/usr/bin/env python3
"""
阶段 3 检索评测：批量跑 eval_set.json，输出 Recall@1/3/5。

运行（在 rag-backend/ 目录）：
    python eval/run_eval.py
    python eval/run_eval.py --mode vector
    python eval/run_eval.py --mode hybrid_rerank --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.engine import SearchMode, search

EVAL_PATH = Path(__file__).resolve().parent / "eval_set.json"
MODES: list[SearchMode] = ["vector", "bm25", "hybrid", "hybrid_rerank"]


def load_eval_set() -> list[dict]:
    with open(EVAL_PATH, encoding="utf-8") as f:
        return json.load(f)


def hit_at_k(hits, expected_sources: list[str], k: int) -> bool:
    for hit in hits[:k]:
        if hit.source_file in expected_sources:
            return True
    return False


def evaluate_mode(mode: SearchMode, items: list[dict], verbose: bool) -> dict:
    r1 = r3 = r5 = 0
    latencies: list[float] = []
    misses: list[str] = []

    for item in items:
        result = search(item["query"], mode=mode, top_k=5)
        latencies.append(result.elapsed_ms)
        expected = item["expected_sources"]
        ok1 = hit_at_k(result.hits, expected, 1)
        ok3 = hit_at_k(result.hits, expected, 3)
        ok5 = hit_at_k(result.hits, expected, 5)
        r1 += int(ok1)
        r3 += int(ok3)
        r5 += int(ok5)
        if verbose and not ok3:
            top = result.hits[0].source_file if result.hits else "(empty)"
            misses.append(f"{item['id']}: expected {expected}, top1={top}")

    n = len(items)
    return {
        "mode": mode,
        "recall@1": r1 / n,
        "recall@3": r3 / n,
        "recall@5": r5 / n,
        "avg_ms": sum(latencies) / n if latencies else 0.0,
        "misses@3": misses,
    }


def main():
    parser = argparse.ArgumentParser(description="阶段 3 检索 Recall 评测")
    parser.add_argument(
        "--mode",
        choices=MODES,
        help="只评测指定模式；默认跑全部四种",
    )
    parser.add_argument("--verbose", action="store_true", help="打印 Recall@3 未命中样例")
    args = parser.parse_args()

    items = load_eval_set()
    modes = [args.mode] if args.mode else MODES

    print("=" * 60)
    print(f"评测集: {EVAL_PATH.name} ({len(items)} 条)")
    print("=" * 60)

    results = []
    for mode in modes:
        print(f"\n>>> 模式: {mode}")
        t0 = time.perf_counter()
        stats = evaluate_mode(mode, items, args.verbose)
        wall = time.perf_counter() - t0
        results.append(stats)
        print(
            f"Recall@1={stats['recall@1']:.1%}  "
            f"Recall@3={stats['recall@3']:.1%}  "
            f"Recall@5={stats['recall@5']:.1%}  "
            f"avg={stats['avg_ms']:.0f}ms  wall={wall:.1f}s"
        )
        if args.verbose and stats["misses@3"]:
            for line in stats["misses@3"]:
                print(f"  ⚠️  {line}")

    print("\n" + "=" * 60)
    print(f"{'模式':<16} {'R@1':>6} {'R@3':>6} {'R@5':>6} {'avg ms':>8}")
    print("-" * 60)
    for s in results:
        print(
            f"{s['mode']:<16} "
            f"{s['recall@1']:>5.1%} "
            f"{s['recall@3']:>5.1%} "
            f"{s['recall@5']:>5.1%} "
            f"{s['avg_ms']:>8.0f}"
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
