"""
Markdown 加载器：从 Jekyll 博客文章中提取结构化数据。

Jekyll 文章格式::

    ---
    title: 标题
    tags: [RAG, LLM]
    date: 2024-01-01
    ---
    ## 正文开始...

本模块职责：
    list_posts         — 扫描目录，列出所有 .md 文件路径
    parse_front_matter — 拆分 YAML front matter 与 Markdown 正文
    load_post          — 读单篇文章，组装为 BlogPost 对象

为什么不把整篇 .md 直接扔进向量库？
    - front matter（layout、permalink 等）是站点配置，不是正文，会污染检索
    - title / tags / date 应作为 metadata 存入 Chroma，用于过滤与溯源
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class BlogPost:
    """单篇博客文章的结构化表示，供 chunker / store 下游使用。"""

    source_file: str       # 文件名，如 "2026-08-06-RAG.md"（用于增量索引时的删除键）
    post_title: str        # 来自 front matter 的 title
    post_date: str         # 来自 front matter 的 date（统一转为字符串）
    post_tags: list[str]   # 标签列表（已归一化为 str 列表，可能为空）
    body: str              # 去掉 front matter 后的 Markdown 正文
    path: Path             # 源文件完整路径


def parse_front_matter(text: str) -> tuple[dict, str]:
    """解析 YAML front matter，返回 (metadata, body)。

    匹配文章开头的 ``---\\n...\\n---\\n`` 块；若无 front matter，
    返回空 dict 与原文全文。
    """
    # re.DOTALL：让 . 也能匹配换行，从而捕获多行 YAML
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}, text

    # safe_load 解析失败或 YAML 为空时返回 None，or {} 兜底为空 dict
    metadata = yaml.safe_load(match.group(1)) or {}
    # match.end() 是第二个 --- 之后的位置，切片得到纯正文
    return metadata, text[match.end():]


def load_post(md_path: Path) -> BlogPost:
    """读取单个 .md 文件，解析 front matter，返回 BlogPost。"""
    raw = md_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)

    # Jekyll 允许 tags 写成列表或单个字符串，统一为 list
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    return BlogPost(
        source_file=md_path.name,
        post_title=str(meta.get("title", "未知标题")),
        post_date=str(meta.get("date", "")),
        post_tags=[str(t) for t in tags],  # 确保每个 tag 都是 str，满足 Chroma metadata 要求
        body=body.strip(),
        path=md_path,
    )


def list_posts(posts_dir: Path) -> list[Path]:
    """返回目录下所有 .md 文件路径，按文件名排序。

    文件名以日期开头（如 2026-08-06-...），sorted 后大致等于时间顺序。
    仅扫描当前目录，不递归子目录。
    """
    return sorted(posts_dir.glob("*.md"))
