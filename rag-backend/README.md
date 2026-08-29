# RAG Backend

个人博客 RAG 智能问答系统 — 后端服务（FastAPI + LangGraph + Chroma + BGE-M3）

**当前阶段**：阶段 2 — 数据处理与知识库构建 ✅

## 快速开始

```bash
cd rag-backend
source .venv/bin/activate

# 全量索引博客（首次或重建知识库）
python -m app.ingestion.index --full

# 增量更新单篇文章
python -m app.ingestion.index --file 2026-08-06-RAG.md

# 查看库内 chunk 数量
python -m app.ingestion.index --stats

# 启动 API
python -m app.main
```

## 目录结构

```
rag-backend/
├── app/
│   ├── config.py
│   ├── main.py
│   ├── graph/              # LangGraph 工作流（阶段 4 扩展）
│   └── ingestion/          # 阶段 2：数据入库
│       ├── loader.py       # front matter 解析
│       ├── chunker.py      # 标题分块 + 递归分块
│       ├── embedder.py     # BGE-M3 向量化
│       ├── store.py        # Chroma upsert
│       ├── pipeline.py     # 流水线编排
│       └── index.py        # CLI 入口
├── scripts/
├── data/chroma/            # 向量库持久化
└── data/models/            # BGE-M3 本地模型
```

## 阶段 2 索引基线（本机实测）

| 指标 | 数值 |
| --- | --- |
| 文章数 | 13 |
| chunk 总数 | 179 |
| 全量索引耗时 | ~534s（CPU，无 GPU） |

## 分块策略

1. 按 `##` 标题切分（保留章节语义）
2. 超长 section 用 `RecursiveCharacterTextSplitter`（512 / overlap 64）
3. 代码块 ``` 尽量保持完整（占位符保护）
4. 每个 chunk 前缀：`【文章标题 > 章节标题】`

## 阶段 1 验证

```bash
python scripts/verify_chroma.py
python scripts/verify_embedding.py
python -m app.main   # /health
```

## 常见问题

**Q: 全量索引很慢？**  
CPU 上 BGE-M3 约 8–15s/batch，179 chunk 约 9 分钟属正常。有 GPU 可在 `embedder.py` 开启 `use_fp16=True`。

**Q: 增量更新如何工作？**  
先 `delete(where source_file=xxx)` 删旧 chunk，再 upsert 新 chunk，不会重复累积。

**Q: socks 代理报错？**  
本地模型已在 `embedder.py` 自动跳过代理；`.env` 中 `EMBEDDING_MODEL` 务必指向本地路径。

**Q: ModelScope 下载锁冲突？**  
见下方 lock 清理步骤。

**Q: 一直显示 Still waiting to acquire lock？**

```bash
ps aux | grep download_model | grep -v grep   # 确认无重复进程
rm -rf data/models/.lock
find data/models -name '*.incomplete' -delete
python scripts/download_model.py
```
