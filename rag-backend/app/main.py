"""
FastAPI 应用入口。

阶段 4：
- /health           健康检查
- /api/v1/chat      SSE 流式问答
- /api/v1/models    可用 LLM 列表
- /graph/hello      LangGraph 三节点示例（阶段 1 保留）

启动（在 rag-backend/ 目录）：
    python -m app.main
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.chat import router as chat_router
from app.config import settings
from app.graph.hello_graph import run_hello_graph
from app.llm.providers import list_providers

app = FastAPI(
    title="Blog RAG API",
    description="个人博客 RAG 智能问答后端（阶段 4：LangGraph + SSE /chat）",
    version="0.2.0",
)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")


class HelloRequest(BaseModel):
    query: str = "RAG 是什么？"


@app.get("/health")
async def health():
    """健康检查。"""
    return {
        "status": "ok",
        "phase": "4-rag-chat",
        "embedding_model": settings.embedding_model,
        "chroma_path": str(settings.chroma_path),
        "llm_providers": [m["name"] for m in list_providers()],
    }


@app.post("/graph/hello")
async def graph_hello(body: HelloRequest):
    """LangGraph 三节点示例（阶段 1 验证用）。"""
    result = run_hello_graph(body.query)
    return {
        "user_input": result["user_input"],
        "processed": result["processed"],
        "final_answer": result["final_answer"],
    }


def main():
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
