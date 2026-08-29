#!/usr/bin/env python3
"""
阶段 1 验证脚本：BGE-M3 Embedding

运行（在 rag-backend/ 目录）：
    python scripts/verify_embedding.py

国内网络建议在运行前设置镜像：
    export HF_ENDPOINT=https://hf-mirror.com

预期输出：
    - 模型加载成功
    - 向量 shape: (1, 1024) 或类似
    - 中英文各一条测试句的向量维度为 1024

Bi-Encoder 原理简述：
    输入文本 → Transformer 编码 → 池化 → 固定维度向量（1024 维）
    语义相近的句子，向量空间中余弦相似度更高。
"""
import os
import sys
from pathlib import Path

# 国内镜像需在 import huggingface 相关库之前设置
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 把 rag-backend/ 加入 sys.path，便于从 scripts/ 直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

# httpx 不支持 socks:// 代理，加载本地模型时清掉，避免误触 HuggingFace
_PROXY_KEYS = (
    "ALL_PROXY", "all_proxy",
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
)


def _prepare_model_env():
    model_path = settings.embedding_model_path
    if Path(model_path).is_dir():
        for key in _PROXY_KEYS:
            os.environ.pop(key, None)
    return model_path


def main():
    model_path = _prepare_model_env()
    print("=" * 50)
    print("阶段 1 验证：BGE-M3 Embedding")
    print("=" * 50)
    print(f"配置: {settings.embedding_model}")
    print(f"实际加载: {model_path}")
    if settings.embedding_is_local:
        print("来源: 本地模型（无需联网）\n")
    else:
        print("来源: HuggingFace（首次需下载，请耐心等待）\n")

    try:
        from FlagEmbedding import BGEM3FlagModel
    except ImportError as e:
        print(f"❌ 缺少 FlagEmbedding: {e}")
        print("   请执行: pip install FlagEmbedding")
        sys.exit(1)

    # use_fp16=False 提高 CPU 兼容性；有 GPU 可改为 True
    model = BGEM3FlagModel(model_path, use_fp16=False)

    test_sentences = [
        "RAG 是检索增强生成技术",
        "Retrieval-Augmented Generation combines search with LLM",
    ]

    for sentence in test_sentences:
        # encode 返回 dict，dense_vecs 是主向量
        output = model.encode([sentence], batch_size=1, max_length=512)["dense_vecs"]
        dim = len(output[0])
        preview = output[0][:5].tolist()
        print(f"✅ 句子: {sentence[:40]}…")
        print(f"   向量维度: {dim}")
        print(f"   前 5 维: {[round(x, 4) for x in preview]}\n")

        if dim != 1024:
            print(f"❌ 期望 1024 维，实际 {dim} 维")
            sys.exit(1)

    print("✅ BGE-M3 Embedding 验证通过（1024 维）")


if __name__ == "__main__":
    main()
