#!/usr/bin/env python3
"""
Python 基础 · 为读懂 chunker.py 而学

用法（在 rag-backend 目录）：
    python scripts/python_basics_for_chunker.py --lesson 1
    python scripts/python_basics_for_chunker.py          # 全部演示

建议：每课先看打印输出，再改「你的练习」区的变量自己试。
"""
from __future__ import annotations

import re
import sys


def lesson1_how_to_read_types():
    """第 1 课：读代码第一步 —— 搞清变量是什么类型"""
    print("\n" + "=" * 60)
    print("第 1 课：怎么知道变量是什么类型？")
    print("=" * 60)

    body = "这是字符串"
    sections = ["第一段", "## 第二节\n内容"]
    count = 42

    print("body     →", repr(body), "  type:", type(body))
    print("sections →", sections, "  type:", type(sections))
    print("sections[0] type:", type(sections[0]))
    print("count    →", count, "  type:", type(count))

    print("\n记住三句话：")
    print("  type(变量)   → 什么类型")
    print("  len(变量)    → 几个元素 / 几个字符")
    print("  repr(变量)   → 看清换行、引号等隐藏内容")


def lesson2_regex_tool():
    """第 2 课：re.compile 不是字符串，是「切分工具」"""
    print("\n" + "=" * 60)
    print("第 2 课：_HEADING_SPLIT_RE 是什么？")
    print("=" * 60)

    # chunker.py 第 34 行同款
    _HEADING_SPLIT_RE = re.compile(r"\n(?=## )")
    print("type(_HEADING_SPLIT_RE) =", type(_HEADING_SPLIT_RE))
    print("→ 这是「工具」，不是切完的结果\n")

    body = """文章开头，还没有标题。
## 什么是 RAG
RAG 是检索增强生成。
## 架构设计
这里有流程图。"""

    sections = _HEADING_SPLIT_RE.split(body)
    print("type(sections) =", type(sections), "  len =", len(sections))
    for i, s in enumerate(sections):
        print(f"\nsections[{i}] (str, {len(s)}字):")
        print(repr(s))


def lesson3_split_by_heading():
    """第 3 课：模拟 _split_by_heading —— 从 list[str] 到 list[tuple]"""
    print("\n" + "=" * 60)
    print("第 3 课：从 sections 提取章节标题")
    print("=" * 60)

    _HEADING_SPLIT_RE = re.compile(r"\n(?=## )")
    body = """前言部分。
## 第一节
内容 A。
## 第二节
内容 B。"""

    sections = _HEADING_SPLIT_RE.split(body)
    result = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        m = re.match(r"^## (.+)", section)
        title = m.group(1).strip() if m else "（无标题）"
        result.append((title, section))

    print("type(result) =", type(result))
    print("len(result)  =", len(result))
    for title, text in result:
        print(f"  标题: {title!r}  正文长度: {len(text)}字")


def lesson4_overlap():
    """第 4 课：chunk_overlap —— 为什么要重叠切？"""
    print("\n" + "=" * 60)
    print("第 4 课：chunk_overlap 直观演示")
    print("=" * 60)

    text = "铺垫" * 30 + "【关键：RAG=检索+生成】" + "后续" * 30
    size = 80

    # 无 overlap：硬切
    print("--- 无 overlap，每 80 字切一刀 ---")
    for i in range(0, min(len(text), 240), size):
        chunk = text[i : i + size]
        marker = " ← 含「关键」" if "关键" in chunk else ""
        print(f"  [{i:3d}:{i+size}] ...{chunk[-25:]}{marker}")

    # 有 overlap
    overlap = 20
    print(f"\n--- overlap={overlap}，每次只前进 {size - overlap} 字 ---")
    start = 0
    idx = 0
    while start < len(text) and idx < 4:
        chunk = text[start : start + size]
        marker = " ← 整句更完整" if "RAG=检索+生成" in chunk else ""
        print(f"  chunk{idx+1} start={start}: ...{chunk[max(0,len(chunk)-35):]}{marker}")
        start += size - overlap
        idx += 1


def lesson5_chunk_post_flow():
    """第 5 课：chunk_post 主流程（把复杂函数当黑盒）"""
    print("\n" + "=" * 60)
    print("第 5 课：chunk_post 在干什么？（只看主流程）")
    print("=" * 60)

    # 假装已经有一个 BlogPost
    post_title = "RAG 入门"
    post_tags = ["RAG", "LLM"]
    body = """## 原理
RAG 是检索增强生成。
## 实践
用向量库检索。"""

    chunk_size = 512
    tags_str = ",".join(post_tags)
    chunk_index = 0
    records = []

    _HEADING_SPLIT_RE = re.compile(r"\n(?=## )")
    for section in _HEADING_SPLIT_RE.split(body):
        section = section.strip()
        if not section:
            continue
        m = re.match(r"^## (.+)", section)
        section_title = m.group(1).strip() if m else "（无标题）"

        prefix = f"【{post_title} > {section_title}】\n"
        # 简化：这里不二次切分，整节作为一个 piece
        piece = section
        chunk_index += 1
        content = prefix + piece.strip()
        records.append({
            "chunk_id": f"demo_chunk_{chunk_index:03d}",
            "content_preview": content[:60] + "...",
            "char_count": len(content),
            "post_tags": tags_str,
        })

    print(f"共生成 {len(records)} 个 chunk:\n")
    for r in records:
        print(f"  {r['chunk_id']} ({r['char_count']}字)")
        print(f"    {r['content_preview']}\n")


def lesson6_code_block_protect():
    """第 6 课：代码块保护 —— 为什么要占位符？（可选，较难）"""
    print("\n" + "=" * 60)
    print("第 6 课：代码块保护（进阶，可先跳过）")
    print("=" * 60)

    text = "说明文字。" * 5 + "\n```python\nprint('hi')\n```\n" + "总结。" * 5
    print("原文长度:", len(text), "字\n")

    _CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    placeholders: dict[str, str] = {}

    def _protect(match: re.Match) -> str:
        key = f"__CODE_{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    protected = _CODE_BLOCK_RE.sub(_protect, text)
    print("保护后（代码块变成短占位符，切分不会截断代码）:")
    print(repr(protected[:120]), "...")
    print("\nplaceholders 字典:")
    for k, v in placeholders.items():
        print(f"  {k} → {repr(v)}")


LESSONS = {
    1: lesson1_how_to_read_types,
    2: lesson2_regex_tool,
    3: lesson3_split_by_heading,
    4: lesson4_overlap,
    5: lesson5_chunk_post_flow,
    6: lesson6_code_block_protect,
}


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--lesson":
        n = int(sys.argv[2])
        LESSONS[n]()
        return

    print("Python 基础 · 共 6 课（为 chunker.py 服务）")
    for fn in LESSONS.values():
        fn()
    print("\n" + "=" * 60)
    print("建议：python scripts/python_basics_for_chunker.py --lesson 1")
    print("=" * 60)


if __name__ == "__main__":
    main()
