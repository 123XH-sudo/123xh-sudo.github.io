"""
LangGraph RAG 工作流：retrieve → 置信度判断 →（generate 在 API 层流式执行）

图负责检索与降级分支；LLM 流式生成在 /chat SSE 中调用，便于逐 token 推送。
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph.state import RAGState, hits_to_sources
from app.llm.prompts import FALLBACK_ANSWER
from app.retrieval.engine import search


def retrieve_node(state: RAGState) -> dict:
    """节点：Hybrid+Rerank 检索，写入 hits / sources / confidence_ok。"""
    query = state.get("query", "").strip()
    if not query:
        return {
            "hits": [],
            "sources": [],
            "confidence_ok": False,
            "answer": FALLBACK_ANSWER,
            "retrieval_mode": "none",
        }

    result = search(query, mode="hybrid_rerank", top_k=settings.retrieval_top_k)
    hits = result.hits
    sources = hits_to_sources(hits)

    confidence_ok = bool(hits) and hits[0].score >= settings.retrieval_confidence_min

    return {
        "hits": hits,
        "sources": sources,
        "confidence_ok": confidence_ok,
        "retrieval_mode": result.mode,
    }


def fallback_node(state: RAGState) -> dict:
    """节点：检索置信度不足时的诚实降级。"""
    return {"answer": FALLBACK_ANSWER}


def route_after_retrieve(state: RAGState) -> str:
    """条件边：是否进入生成（API 层）或 fallback。"""
    if state.get("confidence_ok"):
        return "ok"
    return "fallback"


def build_rag_graph():
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)# 添加检索节点
    graph.add_node("fallback", fallback_node)# 添加降级节点

    graph.add_edge(START, "retrieve")# 添加起始节点到检索节点的边
    graph.add_conditional_edges(# 添加条件边
        "retrieve", # 添加条件边
        route_after_retrieve,
        {"ok": END, "fallback": "fallback"},# 添加条件边到结束节点
    )
    graph.add_edge("fallback", END)# 添加降级节点到结束节点的边
    return graph.compile()


def run_rag_retrieve(query: str, provider: str = "deepseek") -> RAGState:
    """运行检索子图，返回含 hits / confidence_ok 的状态。"""
    app = build_rag_graph()
    initial: RAGState = {
        "query": query,
        "provider": provider,
        "hits": [],
        "sources": [],
        "confidence_ok": False,
        "answer": "",
        "retrieval_mode": "",
    }
    return app.invoke(initial)
