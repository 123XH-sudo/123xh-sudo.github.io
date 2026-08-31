"""LangGraph RAG 工作流共享状态。"""
from __future__ import annotations

from typing import Any, TypedDict

from app.retrieval.types import RetrievalHit


class SourceInfo(TypedDict):
    """返回给前端的引用来源。"""

    title: str # 文章标题
    source_file: str # 源文件名
    section_title: str  # 章节标题
    relevance_score: float # 相关性得分


class RAGState(TypedDict, total=False):
    """RAG 图在节点间传递的状态。"""

    query: str
    provider: str
    hits: list[RetrievalHit]
    sources: list[SourceInfo]
    confidence_ok: bool
    answer: str
    retrieval_mode: str
    error: str


def hit_to_source(hit: RetrievalHit) -> SourceInfo:
    """RetrievalHit → 前端 sources 事件格式。"""
    score = hit.score
    if score < 0:
        # reranker 原始分可能为负，展示时归一到 0~1 区间
        score = max(0.0, min(1.0, 1.0 / (1.0 + abs(score))))
    elif score > 1:
        score = min(1.0, score / 10.0)
    return {
        "title": hit.post_title or hit.source_file,
        "source_file": hit.source_file,
        "section_title": hit.section_title,
        "relevance_score": round(score, 4),
    }


def hits_to_sources(hits: list[RetrievalHit]) -> list[SourceInfo]:
    return [hit_to_source(h) for h in hits]
