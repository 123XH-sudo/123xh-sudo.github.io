"""
博客分块脚本（初版，阶段 1 原型）。

阶段 2 起请使用 rag-backend 入库流水线：
    cd rag-backend && python -m app.ingestion.index --full
"""
import yaml
import os
import re
from pathlib import Path

POSTS_DIR = Path(__file__).parent / "_posts"


def parse_front_matter(text: str) -> tuple[dict, str]:
    """解析 Jekyll 的 YAML front matter，返回 (元数据, 正文)"""
    # front matter 在两个 --- 之间
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not match:
        return {}, text
    metadata = yaml.safe_load(match.group(1)) or {}
    body = text[match.end():]
    return metadata, body


def split_by_heading(body: str) -> list[dict]:
    """
    按 ## 标题切分正文。
    每个 chunk 保留其所属的标题层级，方便后续检索时理解上下文。
    """
    # 按 ## 标题分割（保留标题本身）
    sections = re.split(r'\n(?=## )', body)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 提取当前 section 的标题
        title_match = re.match(r'^## (.+)', section)
        section_title = title_match.group(1).strip() if title_match else "（无标题）"

        chunks.append({
            "section_title": section_title,
            "content": section,
            "char_count": len(section),
        })

    return chunks


def process_all_posts():
    """处理所有博客文章，输出分块结果"""
    all_chunks = []

    for md_file in sorted(POSTS_DIR.glob("*.md")):
        print(f"📄 处理: {md_file.name}")
        raw_text = md_file.read_text(encoding="utf-8")

        # 第1步：分离 front matter 和正文
        meta, body = parse_front_matter(raw_text)

        # 第2步：按标题切分正文
        chunks = split_by_heading(body)

        # 第3步：给每个 chunk 附上文章元数据
        for i, chunk in enumerate(chunks):
            chunk["source_file"] = md_file.name
            chunk["post_title"] = meta.get("title", "未知标题")
            chunk["post_date"] = str(meta.get("date", "未知日期"))
            chunk["post_tags"] = meta.get("tags", [])
            chunk["chunk_id"] = f"{md_file.stem}_chunk_{i+1:02d}"

            all_chunks.append(chunk)

            # 打印摘要
            preview = chunk["content"][:80].replace("\n", " ")
            print(f"  └─ [{chunk['chunk_id']}] {chunk['section_title']} "
                  f"({chunk['char_count']}字) → {preview}...")

    print(f"\n✅ 共生成 {len(all_chunks)} 个 chunk")
    return all_chunks


if __name__ == "__main__":
    process_all_posts()