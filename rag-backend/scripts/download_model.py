#!/usr/bin/env python3
"""
通过 ModelScope 下载 BGE-M3（国内网络推荐）。

用法（在 rag-backend/ 目录）：
    pip install modelscope   # 若未安装
    python scripts/download_model.py

下载完成后，在 .env 中设置：
    EMBEDDING_MODEL=./data/models/Xorbits/bge-m3
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODEL_ID = "Xorbits/bge-m3"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "models"


def main():
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("请先安装: pip install modelscope")
        sys.exit(1)

    print(f"从 ModelScope 下载 {MODEL_ID} …")
    print(f"保存目录: {CACHE_DIR}")
    print("模型约 2.3GB，请耐心等待。\n")

    path = snapshot_download(MODEL_ID, cache_dir=str(CACHE_DIR))
    print(f"\n✅ 下载完成: {path}")
    print("\n请在 .env 中设置:")
    print(f"EMBEDDING_MODEL={path}")


if __name__ == "__main__":
    main()
