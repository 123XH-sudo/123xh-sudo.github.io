# 开发计划

| 属性 | 内容 |
| --- | --- |
| **文档版本** | v1.0.0 |
| **创建日期** | 2026-08-26 |
| **负责人** | 123XH-sudo |
| **状态** | 已评审，待启动阶段 1 |
| **预计总周期** | 8–10 周（按每周 10–15 小时学习节奏） |

---

## 更新记录

| 版本 | 日期 | 变更内容 | 变更人 | 评审状态 |
| --- | --- | --- | --- | --- |
| v1.0.0 | 2026-08-26 | 初版七阶段开发计划 | 123XH-sudo | 已通过 |
| v1.0.1 | 2026-08-26 | 阶段 1 完成，更新状态 | 123XH-sudo | — |

---

## 1. 阶段总览

| 阶段 | 名称 | 预计周期 | 状态 | 博客产出 |
| --- | --- | --- | --- | --- |
| 0 | 文档规范化 | 1 天 | ✅ 完成 | — |
| 1 | 环境搭建与技术栈验证 | 1 周 | ✅ 完成 | 《RAG 项目环境搭建实录》 |
| 2 | 数据处理与知识库构建 | 1–2 周 | ✅ 完成 | 《博客数据入库：从分块到 Chroma》 |
| 3 | 检索系统实现与优化 | 1–2 周 | ⏳ 待启动 | 《Hybrid 检索 + Rerank 实践》 |
| 4 | 问答系统核心逻辑开发 | 1–2 周 | ⏸ 未开始 | 《LangGraph 编排 RAG 工作流》 |
| 5 | 前端界面与交互实现 | 1 周 | ⏸ 未开始 | 《React SSE 流式聊天组件》 |
| 6 | 系统集成与测试优化 | 1 周 | ⏸ 未开始 | 《RAG 系统评测与调优》 |
| 7 | 部署上线与监控维护 | 1 周 | ⏸ 未开始 | 《个人 RAG 服务部署指南》 |

---

## 2. 阶段 0：文档规范化 ✅

### 目标

建立需求、技术栈、开发计划三份规范文档，作为后续各阶段的启动门禁。

### 交付物

- [x] [需求规格说明书](../requirements/REQUIREMENTS.md)
- [x] [技术栈选型文档](../tech-stack/TECH_STACK.md)
- [x] [开发计划](DEVELOPMENT_PLAN.md)（本文档）

### 验收标准

- 三份文档均含版本号、日期、更新记录、负责人
- 需求覆盖功能/性能/体验/边界条件
- 技术栈含替代方案评估
- 七阶段均有目标、任务、验收标准

---

## 3. 阶段 1：环境搭建与技术栈验证

### 3.1 阶段目标

- 搭建 Python / Node.js 开发环境
- 验证 LangGraph、Chroma、BGE-M3、FastAPI 最小可运行示例
- 建立 `rag-backend/` 项目骨架

### 3.2 学习目标

| 知识点 | 掌握程度 |
| --- | --- |
| Python 虚拟环境与依赖管理 | 能独立创建 venv 并安装依赖 |
| LangGraph 最小 StateGraph | 能解释节点、边、状态的概念 |
| Chroma 基本 CRUD | 能手动 add/query/delete collection |
| BGE-M3 本地推理 | 理解 Bi-Encoder 与向量维度 |
| FastAPI 最小 API | 能启动服务并访问 `/docs` |

### 3.3 技术要点

- `uv` 或 `venv` + `pip` 管理 Python 依赖
- HuggingFace 模型缓存目录配置（国内镜像）
- LangGraph `StateGraph` 定义三节点流水线：input → process → output
- Chroma `PersistentClient` 持久化路径
- FastAPI `uvicorn` 热重载开发

### 3.4 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 1.1 | 创建 `rag-backend/` 目录结构与 `requirements.txt` | 开发者 | 2h |
| 1.2 | 编写 `.env.example`（API Key、模型路径、Chroma 路径） | 开发者 | 1h |
| 1.3 | 验证 BGE-M3 加载与单句 Embedding | 开发者 | 3h |
| 1.4 | 验证 Chroma 写入/查询 10 条测试向量 | 开发者 | 2h |
| 1.5 | 编写 LangGraph 三节点 Hello World | 开发者 | 3h |
| 1.6 | 编写 FastAPI `/health` 端点 | 开发者 | 1h |
| 1.7 | 编写项目根 README 启动说明 | 开发者 | 2h |

### 3.5 实现步骤

```
Step 1: mkdir rag-backend && 初始化 Python 项目
Step 2: pip install langgraph langchain chromadb FlagEmbedding fastapi uvicorn
Step 3: scripts/verify_embedding.py — 加载 BGE-M3，打印向量 shape
Step 4: scripts/verify_chroma.py — 创建 collection，add 3 docs，query 1 条
Step 5: app/graph/hello_graph.py — 定义最小 StateGraph
Step 6: app/main.py — FastAPI app + /health
Step 7: 运行验证，记录遇到的问题
```

### 3.6 验收标准

- [x] `python -m app.main` 启动后 `/health` 返回 200
- [ ] BGE-M3 能对中文句子生成 1024 维向量（需本机执行 `download_model.py` + `verify_embedding.py`）
- [x] Chroma 持久化目录重启后数据仍在
- [x] LangGraph 三节点图能 compile 并 invoke
- [ ] 阶段博客草稿完成（含踩坑记录）

### 3.7 阶段面试自测

1. LangGraph 的 State 和 Chain 的 memory 有什么区别？
2. Chroma 的 collection 和 document 是什么关系？
3. Bi-Encoder（Embedding）和 Cross-Encoder（Reranker）的区别？
4. FastAPI 为什么比 Flask 更适合 SSE 场景？

---

## 4. 阶段 2：数据处理与知识库构建

### 4.1 阶段目标

- 将现有 `chunk_blog.py` 升级为生产级 ingestion 模块
- 实现递归分块 + 元数据提取 + BGE-M3 向量化 + Chroma 入库
- 支持全量索引与单文件增量更新

### 4.2 学习目标

| 知识点 | 掌握程度 |
| --- | --- |
| Jekyll front matter 解析 | 能解释为何需剥离 YAML |
| 递归分块 vs 固定分块 | 能说明选型理由 |
| LangChain Document / TextSplitter | 能使用 RecursiveCharacterTextSplitter |
| 增量更新策略 | 能解释 upsert vs 全量 rebuild |

### 4.3 技术要点

- 迁移 `chunk_blog.py` 逻辑至 `app/ingestion/`
- `RecursiveCharacterTextSplitter`：chunk_size=512, chunk_overlap=64
- 保留 `##` 标题作为 chunk 前缀上下文
- metadata：source_file, post_title, post_date, section_title, chunk_id
- CLI 命令：`python -m app.ingestion.index --full` / `--file xxx.md`

### 4.4 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 2.1 | 设计 Ingestion Pipeline 架构 | 开发者 | 2h |
| 2.2 | 实现 MarkdownLoader + front matter 解析 | 开发者 | 4h |
| 2.3 | 实现递归分块（含代码块保护） | 开发者 | 4h |
| 2.4 | 集成 BGE-M3 批量 Embedding | 开发者 | 3h |
| 2.5 | Chroma upsert 与 dedup（按 chunk_id） | 开发者 | 3h |
| 2.6 | CLI 全量/增量索引命令 | 开发者 | 2h |
| 2.7 | 索引全库 `_posts/` 并验证 chunk 数量 | 开发者 | 2h |

### 4.5 验收标准

- [x] 全量索引本仓库所有 `_posts/` 文章，chunk 数 ≥ 30（2026-08-30 实测 **298** / 19 篇）
- [x] 单文件增量更新后，Chroma 中对应 chunk 已更新（总数不重复膨胀；实测重索引 `2026-08-06-RAG.md` 179→179）
- [x] 每个 chunk 含完整 metadata，可通过 metadata 过滤（`verify_ingestion.py` 通过）
- [x] 索引耗时记录在案（全量 ~534s / 13 篇 / CPU；增量单篇 ~30–52s）
- [x] 阶段博客发布（ingestion 系列 7 篇）
- [x] 检索探针：query embed + Chroma query 可返回相关 chunk（Top-1 → `2026-08-06-RAG.md`）

### 4.6 阶段面试自测

1. 为什么按标题分块可能不够，还需要递归分块？
2. chunk_overlap 的作用是什么？
3. 如何判断一篇博客文章是否已被索引过？

---

## 5. 阶段 3：检索系统实现与优化

### 5.1 阶段目标

- 实现向量检索 + BM25 关键词 Hybrid 检索
- 集成 BGE-Reranker 二次排序
- 建立自建评测集，量化 Recall@K

### 5.2 学习目标

| 知识点 | 掌握程度 |
| --- | --- |
| 余弦相似度 vs 欧氏距离 | 能解释 Chroma 默认度量 |
| Hybrid 检索融合策略 | 理解 RRF / 加权融合 |
| Reranker 工作原理 | 能解释为何只对 Top-K 做 Rerank |
| Recall@K 评估方法 | 能构建 ≥20 条评测集并计算指标 |

### 5.3 技术要点

- `app/retrieval/vector_store.py` — Chroma similarity_search
- `app/retrieval/bm25.py` — rank_bm25 或 LangChain BM25Retriever
- `app/retrieval/hybrid.py` — 融合向量与 BM25 分数
- `app/retrieval/reranker.py` — FlagEmbedding reranker
- `eval/eval_set.json` — 问答对 + 期望来源文章
- `eval/run_eval.py` — 批量跑检索并输出 Recall@1/3/5

### 5.4 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 3.1 | 实现纯向量检索 baseline | 开发者 | 3h |
| 3.2 | 实现 BM25 检索 | 开发者 | 3h |
| 3.3 | 实现 Hybrid 融合 | 开发者 | 4h |
| 3.4 | 集成 BGE-Reranker | 开发者 | 4h |
| 3.5 | 构建评测集（≥20 条） | 开发者 | 4h |
| 3.6 | 对比实验：固定分块 vs 递归分块 | 开发者 | 3h |
| 3.7 | 调参：Top-K、Rerank 候选数、融合权重 | 开发者 | 4h |

### 5.5 验收标准

- [x] Hybrid + Rerank 方案 Recall@3 ≥ 70%（2026-08-30 实测 **95.8%**，24 条评测集）
- [ ] 检索延迟 ≤ 500ms（本地 CLI 含模型推理偏慢；长驻 API 下 vector/hybrid 约 600–900ms，rerank 需 GPU 或预热）
- [x] 有对比实验数据（vector / bm25 / hybrid / hybrid_rerank 四组，`eval/run_eval.py`）
- [ ] 阶段博客发布（待 Phase 3 带读学习）

### 5.6 阶段面试自测

1. 什么场景下 BM25 比向量检索更好？
2. Reranker 为什么比 Embedding 慢，如何权衡？
3. Recall@3 = 0.7 意味着什么？

---

## 6. 阶段 4：问答系统核心逻辑开发

### 6.1 阶段目标

- 用 LangGraph 编排完整 RAG 工作流
- 实现 Prompt 构造 + LLM 流式生成
- 提供 `/chat` SSE API

### 6.2 学习目标

| 知识点 | 掌握程度 |
| --- | --- |
| LangGraph 条件边 | 能实现低置信度分支 |
| RAG Prompt 模板设计 | 能解释 system/user/context 分工 |
| SSE 协议 | 能解释 data: 格式与 [DONE] 信号 |
| 引用溯源 | 能在回答中标注来源 |

### 6.3 技术要点

LangGraph 节点设计：

```
START → retrieve → rerank → [confidence check]
                              ├─ high → generate → END
                              └─ low  → fallback_message → END
```

- `app/graph/rag_graph.py` — 完整 StateGraph
- `app/graph/state.py` — RAGState（query, chunks, answer, sources）
- `app/llm/providers.py` — DeepSeek / OpenAI 兼容接口
- `app/api/chat.py` — SSE StreamingResponse
- Prompt 模板：要求基于上下文回答，无法回答时明确说明

### 6.4 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 4.1 | 定义 RAGState 与节点接口 | 开发者 | 3h |
| 4.2 | 实现 retrieve / rerank 节点 | 开发者 | 4h |
| 4.3 | 实现 generate 节点（流式） | 开发者 | 5h |
| 4.4 | 实现条件边（低置信度降级） | 开发者 | 3h |
| 4.5 | 实现 `/chat` SSE 端点 | 开发者 | 4h |
| 4.6 | 实现 `/models` 端点 | 开发者 | 1h |
| 4.7 | curl / Postman 端到端测试 | 开发者 | 2h |

### 6.5 验收标准

- [ ] `POST /chat` 返回 SSE 流，含 status/token/sources/done 事件
- [ ] 回答内容可追溯至检索 chunk
- [ ] 知识库无相关内容时返回诚实降级回答
- [ ] LangGraph 图可用 Mermaid 或 LangSmith 可视化
- [ ] 阶段博客发布

### 6.6 阶段面试自测

1. LangGraph 节点之间如何传递状态？
2. SSE 和 WebSocket 在本项目中为什么选 SSE？
3. 如何防止 LLM 忽略检索上下文产生幻觉？

---

## 7. 阶段 5：前端界面与交互实现

### 7.1 阶段目标

- 用 React 重写聊天 Widget
- 实现 SSE 客户端、Markdown 渲染、来源展示
- 构建产物嵌入 Jekyll 博客

### 7.2 学习目标

| 知识点 | 掌握程度 |
| --- | --- |
| React 函数组件 + Hooks | 能管理 messages 状态 |
| fetch + ReadableStream | 能解析 SSE 事件 |
| react-markdown | 能渲染 LLM 输出 |
| Vite 库模式构建 | 能输出单文件 JS 嵌入 Jekyll |

### 7.3 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 5.1 | 初始化 `rag-frontend/`（Vite + React） | 开发者 | 2h |
| 5.2 | ChatPanel / MessageList / InputBar 组件 | 开发者 | 6h |
| 5.3 | SSE 客户端 hook（useChatStream） | 开发者 | 4h |
| 5.4 | 来源引用展示组件 | 开发者 | 2h |
| 5.5 | 模型选择下拉 | 开发者 | 1h |
| 5.6 | 构建嵌入 `_includes/chat-widget.html` | 开发者 | 3h |
| 5.7 | 移动端适配 | 开发者 | 2h |

### 7.4 验收标准

- [ ] 博客页面右下角 Widget 可正常打开/关闭
- [ ] 提问后流式显示回答，Markdown 格式正确
- [ ] 可展开查看参考来源及相似度
- [ ] 网络错误有友好提示
- [ ] 阶段博客发布

---

## 8. 阶段 6：系统集成与测试优化

### 8.1 阶段目标

- 前后端联调，端到端流程跑通
- 建立评测 pipeline，优化 Prompt 与检索参数
- 替换 Dify 外部依赖，统一为自建后端

### 8.2 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 6.1 | 前后端联调（CORS、API 地址配置） | 开发者 | 3h |
| 6.2 | 端到端评测（≥20 条问答） | 开发者 | 4h |
| 6.3 | Prompt 迭代优化 | 开发者 | 3h |
| 6.4 | 首字延迟优化（并行检索+生成预热） | 开发者 | 3h |
| 6.5 | GitHub Actions 触发增量索引 | 开发者 | 4h |
| 6.6 | 移除/降级 Dify workflow 依赖 | 开发者 | 2h |

### 8.3 验收标准

- [ ] 端到端问答成功率 ≥ 90%（评测集）
- [ ] TTFT ≤ 3s
- [ ] push 新博客文章后 CI 自动触发索引更新
- [ ] 阶段博客发布（含评测报告）

---

## 9. 阶段 7：部署上线与监控维护

### 9.1 阶段目标

- Docker 容器化后端服务
- 部署至个人服务器，配置反向代理
- 建立基础健康检查与日志

### 9.2 任务分解

| 序号 | 任务 | 责任人 | 预计耗时 |
| --- | --- | --- | --- |
| 7.1 | 编写 Dockerfile + docker-compose.yml | 开发者 | 4h |
| 7.2 | Nginx/Caddy 反向代理 + HTTPS | 开发者 | 3h |
| 7.3 | 环境变量与密钥管理 | 开发者 | 2h |
| 7.4 | 健康检查与自动重启 | 开发者 | 2h |
| 7.5 | 更新博客 Widget API 地址 | 开发者 | 1h |
| 7.6 | 编写运维文档（重启、日志、备份） | 开发者 | 2h |

### 9.3 验收标准

- [ ] `docker compose up` 一键启动后端
- [ ] 公网可访问 `/health` 和 `/chat`
- [ ] 博客 Widget 连接生产 API 正常工作
- [ ] 阶段博客发布（部署实录）

---

## 10. 资源需求

| 资源 | 说明 |
| --- | --- |
| 开发机器 | ≥ 8GB RAM（BGE 模型加载），建议 16GB |
| GPU | 可选，CPU 推理可接受但较慢 |
| 磁盘 | ≥ 5GB（模型缓存 + Chroma 数据） |
| LLM API | DeepSeek API Key（按量付费） |
| 服务器 | 1 核 2G 可跑后端（不含模型推理时可 API 化 Embedding） |
| 域名/隧道 | 已有（cloudflare tunnel / lhr.life） |

---

## 11. 风险评估与应对

| 风险 | 概率 | 影响 | 应对措施 |
| --- | --- | --- | --- |
| BGE 模型下载失败 | 中 | 阶段 1 阻塞 | 配置 HF 镜像；提供网盘备份 |
| Recall 不达标 | 中 | 阶段 3 延期 | 增加评测集；尝试不同分块参数 |
| LLM API 不稳定 | 低 | 阶段 4 阻塞 | 多 Provider 降级 |
| React 嵌入 Jekyll 构建复杂 | 中 | 阶段 5 延期 | 先用独立页面验证，再嵌入 Widget |
| 部署环境资源不足 | 低 | 阶段 7 延期 | Embedding 与 Rerank 放本地，仅 API 部署生成服务 |

---

## 12. Git 提交规范

每个功能模块完成后提交，commit message 格式：

```
<type>(<scope>): <subject>

<body — 解决了什么问题>
```

**type**：feat / fix / docs / refactor / test / chore  
**scope**：ingestion / retrieval / graph / api / frontend / deploy

**示例**

```
feat(ingestion): 实现递归分块与 Chroma 增量入库

- 迁移 chunk_blog.py 至 app/ingestion/
- 支持 --full 和 --file 两种索引模式
- 解决代码块被截断的问题
```

---

## 13. 阶段启动检查清单

每个阶段正式启动前，确认：

- [ ] 需求文档为最新版本，本阶段相关需求无变更 pending
- [ ] 技术栈文档为最新版本
- [ ] 上一阶段验收标准已全部通过
- [ ] 本阶段学习目标、任务分解已阅读
- [ ] 开发环境就绪

**当前下一步：启动阶段 1 — 环境搭建与技术栈验证**
