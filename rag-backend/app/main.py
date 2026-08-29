"""
FastAPI 应用入口。

阶段 1 目标：
- /health  健康检查（部署、Docker 探针会用到）
- /graph/hello  验证 LangGraph 三节点图可运行

启动方式（在 rag-backend/ 目录下）：
    python -m app.main
    # 或
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from app.config import settings
from app.graph.hello_graph import run_hello_graph

app = FastAPI(
    title="Blog RAG API",
    description="个人博客 RAG 智能问答后端（阶段 1：环境验证）",
    version="0.1.0",
)


class HelloRequest(BaseModel):
    query: str = "RAG 是什么？"


@app.get("/health")
async def health():
    """健康检查：确认服务进程正常。"""
    return {
        "status": "ok",
        "phase": "1-environment-verification",
        "embedding_model": settings.embedding_model,
        "chroma_path": str(settings.chroma_path),
    }


@app.post("/graph/hello")
async def graph_hello(body: HelloRequest):
    """
    运行 LangGraph 三节点示例图。

    用于验证 LangGraph 依赖与 StateGraph 编排是否正常。
    """
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
