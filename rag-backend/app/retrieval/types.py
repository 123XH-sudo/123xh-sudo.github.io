"""检索模块共享类型。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalHit:
    """单条检索结果。"""

    chunk_id: str
    content: str
    metadata: dict
    score: float = 0.0  # 越高越相关（各检索器统一方向）
    distance: float | None = None  # 向量检索原始距离，越小越相似
    rank_source: str = ""  # vector / bm25 / hybrid / rerank

    @property
    def source_file(self) -> str:
        return self.metadata.get("source_file", "")# 获取源文件名

    @property
    def post_title(self) -> str:
        return self.metadata.get("post_title", "")# 获取文章标题

    @property
    def section_title(self) -> str:
        return self.metadata.get("section_title", "")# 获取章节标题


@dataclass
class RetrievalResult:
    """一次检索的完整结果。"""

    query: str
    hits: list[RetrievalHit]
    elapsed_ms: float
    mode: str = "vector"
