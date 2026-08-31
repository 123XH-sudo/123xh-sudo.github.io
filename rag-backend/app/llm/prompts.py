"""RAG Prompt 模板。"""
from __future__ import annotations

from app.retrieval.types import RetrievalHit

SYSTEM_PROMPT = """你是个人博客「123XH-sudo」的问答助手。
规则：
1. 仅根据用户提供的「参考资料」回答，不要编造资料中没有的内容。
2. 若参考资料不足以回答问题，请明确说明「根据博客现有内容无法确定」，不要猜测。
3. 使用与用户问题相同的语言（中文优先）。
4. 回答简洁清晰，可适度使用 Markdown。"""


def format_context(hits: list[RetrievalHit]) -> str:
    """把检索 chunk 格式化为 Prompt 上下文。"""
    if not hits:
        return "（无参考资料）"

    blocks: list[str] = []
    for i, hit in enumerate(hits, start=1):
        header = f"[{i}] {hit.post_title} > {hit.section_title} ({hit.source_file})"
        blocks.append(f"{header}\n{hit.content.strip()}")
    return "\n\n---\n\n".join(blocks)


def build_chat_messages(query: str, hits: list[RetrievalHit]) -> list[dict[str, str]]:
    """构造 OpenAI 兼容 chat messages。"""
    context = format_context(hits)
    user_content = f"""参考资料：
{context}

用户问题：{query}"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


FALLBACK_ANSWER = (
    "抱歉，我在博客知识库中没有找到足够相关的内容来回答这个问题。"
    "你可以换个问法，或确认该主题是否已在博客文章中写过。"
)
