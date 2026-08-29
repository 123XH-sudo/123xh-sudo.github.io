# 123xh-sudo.github.io

个人技术博客 + RAG 智能问答系统学习项目。

## 项目文档

开发流程遵循「需求确认 → 技术栈确定 → 开发计划评审 → 阶段开发」规范，文档位于 [`docs/`](docs/)：

| 文档 | 说明 |
| --- | --- |
| [需求规格说明书](docs/requirements/REQUIREMENTS.md) | 功能、性能、体验、边界条件 |
| [技术栈选型文档](docs/tech-stack/TECH_STACK.md) | 选型理由与替代方案 |
| [开发计划](docs/plan/DEVELOPMENT_PLAN.md) | 七阶段任务与验收标准 |

**当前阶段**：阶段 2 知识库构建 ✅ → 待启动 **阶段 3：检索系统实现与优化**

## 知识库索引（阶段 2）

```bash
cd rag-backend && source .venv/bin/activate
python -m app.ingestion.index --full    # 全量索引
python -m app.ingestion.index --stats   # 查看 chunk 数
```

## 仓库结构

```
├── _posts/              # Jekyll 博客文章（RAG 数据源）
├── docs/                # 项目规范文档
├── chunk_blog.py        # 博客分块脚本（初版，将迁入 rag-backend）
├── _includes/           # Jekyll 模板（含聊天 Widget）
└── rag-backend/         # 阶段 1 起创建：FastAPI + LangGraph + Chroma
```

## 技术栈

LangGraph · LangChain · Chroma · BGE-M3 · BGE-Reranker · FastAPI · React

## 本地运行（博客）

```bash
bundle install
bundle exec jekyll serve
```

访问 http://localhost:4000

## 相关博客

- [RAG 系统基础：从原理到架构](_posts/2026-08-06-RAG.md)
- [个人博客数据处理](_posts/2026-08-06-blog-data-processing.md)
- [向量数据库选型](_posts/2026-08-08-vector-database.md)
