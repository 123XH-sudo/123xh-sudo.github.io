"""
分块策略：先按 ## 标题切分（语义边界），再对过长 section 递归切分。

两阶段分块的原因（阶段 2 面试题）：
1. 仅按标题：单节超长（如大段代码+讲解）会超出 embedding 有效窗口
2. 仅固定长度：可能在段落/代码块中间截断，破坏语义
3. 组合策略：标题保结构，递归保长度上限

chunk_overlap 的作用：相邻 chunk 共享 64 字上下文，避免关键句被截在边界上导致检索丢失。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.loader import BlogPost


@dataclass
class ChunkRecord:
    chunk_id: str
    content: str
    source_file: str
    post_title: str
    post_date: str
    post_tags: str  # Chroma metadata 只支持标量，tags 用逗号连接
    section_title: str
    char_count: int


_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_HEADING_SPLIT_RE = re.compile(r"\n(?=## )")


def _split_by_heading(body: str) -> list[tuple[str, str]]:
    """返回 [(section_title, section_text), ...]"""
    sections = _HEADING_SPLIT_RE.split(body)
    result: list[tuple[str, str]] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        m = re.match(r"^## (.+)", section)
        title = m.group(1).strip() if m else "（无标题）"
        result.append((title, section))
    return result


def _split_preserving_code(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    对超长 section 分块，尽量保持 ``` 代码块完整。

    思路：先把代码块替换成占位符 → 递归分块 → 还原占位符。
    """
    placeholders: dict[str, str] = {}

    def _protect(match: re.Match) -> str:
        key = f"__CODE_{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    protected = _CODE_BLOCK_RE.sub(_protect, text)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
        length_function=len,
    )
    parts = splitter.split_text(protected)
    restored: list[str] = []
    for part in parts:
        for key, code in placeholders.items():
            part = part.replace(key, code)
        restored.append(part)
    return restored


def chunk_post(
    post: BlogPost,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[ChunkRecord]:
    """将一篇博客转为可入库的 chunk 列表。"""
    tags_str = ",".join(post.post_tags)
    stem = post.path.stem
    records: list[ChunkRecord] = []
    chunk_index = 0

    for section_title, section_text in _split_by_heading(post.body):
        # 在 chunk 正文前加标题前缀，检索时能感知章节上下文
        prefix = f"【{post.post_title} > {section_title}】\n"
        pieces = (
            [section_text]
            if len(section_text) <= chunk_size
            else _split_preserving_code(section_text, chunk_size, chunk_overlap)
        )

        for piece in pieces:
            chunk_index += 1
            content = prefix + piece.strip()
            records.append(
                ChunkRecord(
                    chunk_id=f"{stem}_chunk_{chunk_index:03d}",
                    content=content,
                    source_file=post.source_file,
                    post_title=post.post_title,
                    post_date=post.post_date,
                    post_tags=tags_str,
                    section_title=section_title,
                    char_count=len(content),
                )
            )

    return records
