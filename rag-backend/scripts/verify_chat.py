#!/usr/bin/env python3
"""
阶段 4 验证：RAG 检索子图 + /chat API smoke test。

运行（在 rag-backend/ 目录）：
    python scripts/verify_chat.py

需已索引 Chroma；完整 LLM 流式测试需配置 DEEPSEEK_API_KEY。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.graph.rag_graph import run_rag_retrieve
from app.llm.providers import list_providers


def main():
    print("=" * 50)
    print("阶段 4 验证：RAG 检索 + API")
    print("=" * 50)

    # 1. LangGraph retrieve
    query = "什么是 RAG？"
    print(f"\n[1] run_rag_retrieve: {query!r}")
    state = run_rag_retrieve(query)
    hits = state.get("hits") or []
    if not hits:
        print("❌ 检索无结果")
        sys.exit(1)
    top = hits[0].source_file
    ok = top == "2026-08-06-RAG.md"
    mark = "✅" if ok else "⚠️ "
    print(f"{mark} hits={len(hits)} confidence_ok={state.get('confidence_ok')} top1={top}")

    # 2. providers
    providers = list_providers()
    print(f"\n[2] LLM providers: {[p['name'] for p in providers]}")
    if not providers:
        print("⚠️  未配置 DEEPSEEK_API_KEY，/chat 仅能 fallback，无法流式生成")

    # 3. FastAPI routes
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    health = client.get("/health")
    if health.status_code != 200:
        print(f"❌ /health 失败: {health.status_code}")
        sys.exit(1)
    models = client.get("/api/v1/models")
    if models.status_code != 200:
        print(f"❌ /api/v1/models 失败: {models.status_code}")
        sys.exit(1)
    print(f"\n[3] /health OK, /models → {models.json()}")

    print("\n✅ 阶段 4 smoke test 通过")
    if settings.deepseek_api_key:
        print("   完整 SSE 测试: python -m app.main")
        print('   curl -N -X POST http://localhost:8000/api/v1/chat \\')
        print('     -H "Content-Type: application/json" \\')
        print(f'     -d {json.dumps({"query": query, "provider": "deepseek"})}')


if __name__ == "__main__":
    main()
