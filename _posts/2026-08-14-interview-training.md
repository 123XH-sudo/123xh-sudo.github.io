---
layout: single
title: "AI 应用开发面试突击指南：从简历项目到面试通关"
date: 2026-08-14 12:00:00 +0800
categories: 
  - 学习笔记
tags:
  - 面试
  - RAG
  - LangChain
  - LangGraph
  - Docker
  - Agent
  - 职业规划

toc: true
toc_sticky: true
---

> 最近开始了 AI 应用开发方向的求职，投简历前先给自己做了一次系统性的面试突击培训。本文整理了基础短板、RAG 核心栈、项目话术和常见陷阱题，适合把简历项目"讲透彻"。

---

## 一、基础短板速补（面试官最爱问）

### 1.1 Docker 常用命令

面试官问「列举 Docker 容器的命令」，标准回答：

```bash
# 容器生命周期
docker ps           # 列出运行中的容器
docker ps -a        # 列出所有容器（含已停止的）
docker run -d -p 8080:80 --name myapp nginx  # 启动容器
docker stop myapp   # 停止容器
docker start myapp  # 启动已停止的容器
docker restart myapp
docker rm myapp     # 删除容器（需先 stop）
docker rm -f myapp  # 强制删除运行中的容器

# 进入容器 / 查看日志
docker exec -it myapp /bin/bash   # 进入容器内部
docker logs -f myapp              # 实时查看日志
docker logs --tail 100 myapp      # 看最后 100 行

# 镜像管理
docker images       # 列出本地镜像
docker pull python:3.11  # 拉取镜像
docker rmi image_id  # 删除镜像
docker build -t myapp:v1 .  # 构建镜像

# Compose
docker-compose up -d    # 后台启动所有服务
docker-compose down     # 停止并删除
docker-compose logs -f  # 查看所有服务日志
```

**面试话术**：日常开发中我常用 `docker ps -a` 查看容器状态，用 `docker exec -it` 进入容器排查问题，部署时用 `docker-compose up -d` 一键启动整个服务栈。

### 1.2 PostgreSQL vs MySQL

| 特性 | MySQL | PostgreSQL |
|------|-------|------------|
| 向量扩展 | 不支持 | 有 **pgvector** 插件，可以存向量 |
| JSON 支持 | 有 JSON 类型 | JSONB 类型，查询更快 |
| 并发 | 表级锁多 | MVCC 更优，高并发更好 |
| 适合场景 | 简单 CRUD | 复杂查询 + 向量检索混合 |

**面试话术**：在电商客服 RAG 项目中选 PostgreSQL 是因为它支持 pgvector 扩展，可以把向量和业务数据存在同一个库里，减少数据同步复杂度。另外 JSONB 类型对半结构化数据（如商品属性）很友好。

### 1.3 Redis 核心用法

五大基本数据类型：String、Hash、List、Set、Sorted Set。

**面试话术**：Redis 在我的项目中主要有两个用途：

1. **缓存层**：缓存热点问答对，减少向量检索次数，提升响应速度
2. **会话管理**：在语音陪伴 Agent 中，用 Redis 的 Hash 结构存储用户长期记忆，设置 TTL 过期时间做记忆衰减

### 1.4 SSE（Server-Sent Events）流式响应

面试官可能问「SSE 和 WebSocket 有什么区别？」

**标准回答**：SSE 是单向的，服务器到客户端推送，基于 HTTP 协议，天然支持断线重连。WebSocket 是双向全双工。

在 RAG 项目中，我用 SSE 实现流式回答，因为 LLM 生成 token 的过程天然适合逐字推送。前端用 EventSource API 接收，后端 FastAPI 用 `StreamingResponse` 返回。首字延迟控制在 1 秒以内。

### 1.5 高频专业术语速查

| 术语 | 一句话解释 |
|------|-----------|
| CI/CD | 持续集成/持续部署，代码 push 后自动测试、构建、部署 |
| Git Flow | 分支策略：main(生产) → develop(开发) → feature/xxx(功能分支) |
| Nginx 反向代理 | 客户端请求 → Nginx → 后端服务，隐藏后端真实地址，做负载均衡 |
| MVCC | 多版本并发控制，数据库在不加锁的情况下实现高并发读写 |
| RPC | 远程过程调用，像调本地函数一样调远程服务（gRPC、Dubbo） |
| 消息队列 | 异步解耦工具（RabbitMQ、Kafka），削峰填谷 |
| 微服务 | 把一个大应用拆成多个独立小服务，各自部署 |

---

## 二、RAG 核心技术栈深度串讲

面试官问 RAG 时，你需要能讲出这条链路：

```
用户提问 → Embedding 向量化 → 向量库检索 → 粗排(Top-K) → Rerank 精排 → 拼接 Prompt → LLM 生成 → 流式返回
```

### 2.1 Embedding 模型

BGE-M3 是 BAAI 出品，支持多语言，8192 token 长度，1024 维向量。

**面试话术**：选 BGE-M3 是因为它中文效果好，且支持长文本，适合博客文章这种长文档场景。

### 2.2 Chunking 分块策略

- 递归分块（RecursiveCharacterTextSplitter）：按 `\n\n` → `\n` → `。` 优先级切分
- chunk_size 一般 500-1000，overlap 约 10%-20%

**面试话术**：递归分块比固定长度分块好，因为尽量保持段落完整性，减少语义割裂。

### 2.3 向量库选型：Chroma vs Milvus

| 维度 | Chroma | Milvus |
|------|--------|--------|
| 定位 | 轻量级，本地开发 | 分布式，生产环境 |
| 规模 | 万级向量 | 十亿级向量 |
| 部署 | pip install 即用 | 需要 Docker 部署 |

**面试话术**：博客项目用 Chroma 快速验证，电商项目用 Milvus 因为要支撑百万级 SKU 的向量检索。

### 2.4 Hybrid Search 混合检索

- 关键词检索（BM25/Elasticsearch）+ 向量检索（语义相似度）
- 结果融合：RRF（Reciprocal Rank Fusion）算法合并两个排序结果

**面试话术**：纯向量检索对专有名词、型号等关键词不敏感，加上 BM25 关键词检索做互补，召回率提升明显。

### 2.5 Rerank 重排序

BGE-Reranker 是 Cross-Encoder，把 query 和每个候选文档拼在一起打分。比 Bi-Encoder（Embedding 模型）更准确，但更慢，所以只对 Top-K 做 Rerank。

**面试话术**：先向量检索召回 Top-20，再用 Reranker 精排取 Top-3，兼顾速度和精度。

---

## 三、逐项目面试话术

### 项目 1：个人博客 RAG 智能问答系统

**Q: 介绍一下这个项目**

> 这是我独立从零搭建的端到端 RAG 系统，解决个人博客文章量大、传统关键词搜索找不到想要内容的问题。
>
> 技术架构上，我用了 LangGraph 做工作流编排，把整个 RAG 流程拆成文档加载→分块→向量化→检索→重排→生成 这些节点，每个节点是一个独立的状态，方便调试和扩展。对比之前用 LangChain 的 Chain 方案，LangGraph 的图结构让我能灵活插入新节点，比如后来加了一个「问题改写」节点来优化多轮对话。
>
> 检索方面，我踩过坑——最开始用固定长度分块，长文章被切碎导致检索不准。后来改成递归分块，加上 BGE-Reranker 做二次排序，Top-3 命中率提升很明显。
>
> 前端用 React，后端 FastAPI 返回 SSE 流式响应，首字延迟控制在 1 秒左右。

**Q: LangGraph 和 LangChain 的 Chain 有什么区别？**

> Chain 是线性的，A→B→C 固定流程。LangGraph 是图结构，节点之间可以有条件分支、循环。比如检索后发现相关度低，可以走「联网搜索」分支，或者走「澄清追问」分支。这个灵活性 Chain 做不到。

**Q: 增量更新机制怎么做的？**

> 博客文章新增或修改时，我通过文件监听触发增量索引——只对新文档做分块和向量化，追加到 Chroma 里，不用全量重建索引。这样更新耗时从分钟级降到秒级。

---

### 项目 2：对话式语音智能体

**Q: 人格复刻怎么做的？**

> 核心思路是从真实对话数据中提取人格特征。我定义了三个维度：对话风格（正式/随意）、情感模式（乐观/悲观/中性）、知识偏好（技术/生活/哲学）。然后从大量真实对话中统计这些维度的分布，用这些统计结果约束 System Prompt。
>
> 比如某人的对话数据显示 70% 的回复偏随意、爱用表情包，我就在 System Prompt 里写「你是一个随和的人，喜欢用轻松的语气交流，偶尔用表情包表达情绪」。

**Q: 长期记忆怎么防止无关回忆？**

> 我设计了一个记忆相关性评分机制。每次用户发新消息，先用 Embedding 计算和所有历史记忆的相似度，只取 Top-K 相关的记忆注入 Prompt。同时设置记忆衰减——越久远的记忆权重越低，超过 30 天没被调用的记忆自动归档。

**Q: 人格漂移是什么，怎么解决的？**

> 长对话中，模型会逐渐忘记初始的 System Prompt 设定，回复风格慢慢偏离——这就是人格漂移。我的方案是「角色摘要缓冲记忆」：每 10 轮对话后，用一个 LLM 调用把最近的对话摘要成一段描述，注入到下一轮上下文中，相当于定期提醒模型「你是谁」。

**Q: 语音交互怎么实现的？**

> 前端用浏览器的 Web Speech API：SpeechRecognition 做语音转文字，SpeechSynthesis 做文字转语音。后端只处理文本，语音部分完全在前端完成，降低服务端压力。

---

### 项目 3：电商客服 RAG 系统

**Q: 最大的挑战是什么？**

> 最大的挑战是检索精度。电商场景下，用户问「iPhone 15 和 15 Pro 有什么区别」，如果向量检索只返回了 iPhone 15 的文档，就会漏掉关键信息。
>
> 我的方案是 Hybrid Search + Rerank 两阶段检索：
> - 第一阶段：BM25 关键词检索 + 向量语义检索并行，各取 Top-20，用 RRF 算法融合取 Top-10
> - 第二阶段：Cross-Encoder Reranker 精排，取 Top-3
>
> 这样既能召回关键词精确匹配的文档，也能召回语义相关的文档。

**Q: 兜底机制怎么做的？**

> 文档版本号 + 定时校验。每个知识库文档带版本号，每小时跑一个定时任务对比线上版本和数据库版本，不一致的自动标记为过期。用户提问时，过期文档不会进入检索池。这样避免了「双十一活动已结束但客服还在推荐」这种事故。

**Q: 多轮追问怎么优化？**

> 核心是问题改写。比如用户先问「iPhone 15 多少钱」，然后问「那 Pro 呢？」，如果不做改写，直接拿「那 Pro 呢？」去检索，什么都搜不到。我用了一个轻量 LLM 把后续追问改写成完整问题，比如「iPhone 15 Pro 多少钱」，然后再检索，命中率大幅提升。

---

## 四、LangChain / LangGraph 核心概念

### Tool Calling 机制

> Tool Calling 是让 LLM 能调用外部函数的能力。流程是：用户提问 → LLM 判断需要调用哪个工具 → 返回工具名和参数 → 程序执行工具 → 结果返回给 LLM → LLM 生成最终回答。
>
> 在实习项目中，我封装了工单查询、库存检索等 API 为 LangChain Tool，Agent 根据用户意图自动选择调用哪个。

### ReAct Agent

> ReAct = Reasoning + Acting。Agent 交替进行「思考」和「行动」：先思考下一步该做什么，然后执行工具调用，观察结果，再思考下一步。这个循环直到 Agent 认为有足够信息回答用户为止。

### MCP 协议

> MCP（Model Context Protocol）是 Anthropic 提出的 Agent 与外部工具之间的标准协议。类比 USB 协议——MCP 就是 Agent 和工具之间的「统一接口」。
>
> 我基于 MCP 开发了文件读写和 API 编排的 Skill，实现 Agent 权限隔离——不同 Skill 有不同的访问范围，防止 Agent 越权操作。

---

## 五、高频陷阱题

### Q: RAG 系统准确率是多少？

> 我在自建评测集上做了测试，包含 200 条真实用户问题。最初纯向量检索 Top-3 命中率约 65%，加入 Hybrid+Rerank 后提升到 88% 左右。但我很清楚评测集不代表线上真实分布，所以实际部署后还持续收集 bad case 做优化。

### Q: 向量检索为什么快？

> 核心是 ANN（近似最近邻）算法，比如 HNSW（分层可导航小世界图）。不是暴力比较所有向量，而是通过图结构快速定位到近似区域，复杂度从 O(n) 降到 O(log n)。Milvus 底层就用 HNSW 索引。

### Q: RAG 和微调有什么区别？

> RAG 是给 LLM 外挂知识库，知识实时更新，可解释性强（能溯源到具体文档）。微调是改变模型参数，成本高，更新需要重新训练。我的场景是博客内容频繁更新，RAG 比微调更合适。

### Q: FastAPI 为什么快？

> FastAPI 基于 Starlette（异步框架）和 Pydantic（数据校验），原生支持 async/await。对比 Flask，它不是阻塞式处理请求，IO 密集场景下性能差距明显。开发效率也高，自动生成 OpenAPI 文档。

### Q: Docker 和直接部署有什么区别？

> Docker 解决「在我机器上能跑」的问题。镜像打包了代码+依赖+运行环境，在任何机器上行为一致。另外 Docker Compose 能一键启动 Redis + PostgreSQL + 应用，比手动配置环境省太多时间。

### Q: 你遇到的最大技术难点是什么？

> 长文档检索的召回率问题。我的博客里有 5000 字以上的长文，切分后单个 chunk 缺乏完整上下文，检索不准。我试了三种方案：
> 1. 加大 chunk_size → 检索粒度太粗
> 2. 父子文档索引（小粒度检索，大粒度返回）→ 效果好但实现复杂
> 3. 递归分块 + Rerank → 最终采用
>
> 这个过程中我学到了：没有银弹，需要根据场景做 trade-off。

---

## 六、面试前快速复习清单

| 考点 | 关键词 |
|------|--------|
| RAG 流程 | 分块→向量化→检索→Rerank→生成 |
| 向量库 | Chroma(轻量) / Milvus(分布式) |
| 检索策略 | Hybrid Search(向量+BM25) + RRF 融合 + Rerank 精排 |
| LangGraph | 图结构编排，节点+边+条件分支 |
| ReAct Agent | 思考→行动→观察→循环 |
| Docker | ps / logs / exec / compose up |
| SSE | 单向推送，EventSource，StreamingResponse |
| Redis | 缓存/会话，5 种数据类型，TTL 过期 |
| PostgreSQL | pgvector 扩展，JSONB，MVCC 并发 |
| 人格漂移 | 角色摘要缓冲记忆，定期压缩历史 |
| 多轮对话 | 问题改写，指代消解 |

---

## 七、面试心态建议

1. **诚实但自信**：如果你被问到没做过的细节，可以说「这部分我用了开源的方案，具体实现细节我需要再确认一下」，比直接说「不知道」好得多。

2. **引导面试官**：当被问到不熟悉的东西时，把话题拉回你准备好的领域。比如「Docker 的底层我不是很深入，但我能讲一下我怎么用 Docker Compose 管理整个服务栈的」。

3. **现在立刻去做的**：
   - 把 `docker ps`、`docker exec` 等命令在终端里敲一遍，形成肌肉记忆
   - 用 Docker 跑一个 PostgreSQL 容器，亲自 `docker exec` 进去看看
   - 在 DIFY 上跑通的 RAG 流程，把每一步都截图，理解每一步在做什么

---

> 本文会持续更新，欢迎补充更多面试真题和回答策略。