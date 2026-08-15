---
layout: single
title: "面试突击学习笔记：Docker、Redis、SSE、Hybrid Search 详解"
date: 2026-08-15 12:00:00 +0800
categories: 
  - 学习笔记
tags:
  - Docker
  - Redis
  - SSE
  - PostgreSQL
  - Hybrid Search
  - RAG
  - 面试

toc: true
toc_sticky: true
---

> 本文是面试突击学习的第二篇笔记，整理了 Docker 常用命令记忆法、Redis 五大数据类型、SSE 流式响应、PostgreSQL 核心概念以及 Hybrid Search 混合检索原理。每个知识点都从"是什么、怎么记、面试怎么讲"三个角度展开。

---

## 一、Docker 命令速记

### 1.1 启动容器：`docker run`

```
docker run -d -p 8080:80 --name myapp nginx
      ↓    ↓       ↓           ↓        ↓
    启动  后台   端口映射    起名字    镜像名
```

| 参数 | 全称 | 怎么记 |
|------|------|--------|
| `-d` | **d**etach | 后台跑，别占终端 |
| `-p 8080:80` | **p**ort | 左边电脑端口，右边容器端口 |
| `--name` | — | 起名字，不然随机名很难记 |
| 镜像名 | — | 放最后，跟 `python script.py` 一样 |

**记忆技巧**：`-d` 在前面（最常用），`-p` 和 `--name` 顺序无所谓，镜像名永远在最后。

---

### 1.2 进入容器：`docker exec -it`

```
docker exec -it myapp /bin/bash
      ↓     ↓    ↓      ↓
    执行  终端  容器名  打开shell
```

| 参数 | 全称 | 含义 |
|------|------|------|
| `exec` | **exec**ute | 在容器里执行命令 |
| `-i` | **i**nteractive | 保持输入，让你能敲键盘 |
| `-t` | **t**ty | 分配终端，给你正常命令行界面 |

**记忆口诀**：`-it` = "**I** want a **T**erminal"（我要一个终端）。

**为什么 `-i` 和 `-t` 必须一起用？** 只有 `-i`：能输入但界面丑；只有 `-t`：界面好看但键盘传不进去；`-it` 一起：既有交互又有正常终端体验。

**`/bin/bash` 是固定的吗？** 不是。大部分容器用 `/bin/bash`，精简容器（如 Alpine）只有 `sh`。先试 `bash`，报错换 `sh`。

---

### 1.3 查看日志：`docker logs`

```bash
docker logs myapp           # 一次性输出历史日志
docker logs -f myapp        # 实时跟随（-f = follow）
docker logs --tail 50 myapp # 只看最后 50 行
```

---

### 1.4 同一个 `-f`，不同含义

| 命令 | `-f` 含义 | 全称 |
|------|----------|------|
| `docker logs -f` | 跟随 | **f**ollow |
| `docker rm -f` | 强制 | **f**orce |

**记法**：看动词判断。`logs` 是"看"，所以是 follow；`rm` 是"删"，所以是 force。

---

### 1.5 镜像管理

```bash
docker pull python:3.11     # 拉取镜像（镜像名:版本标签）
docker images               # 列出本地镜像，看 IMAGE ID 列
docker rmi image_id         # 删除镜像（rmi = remove image）
docker build -t myapp:v1 .  # 构建镜像（-t = tag 打标签）
```

**`docker build` 拆解**：

```
docker build -t myapp:v1 .
      ↓       ↓     ↓    ↓
    构建    打标签  名字  当前目录（找Dockerfile）
```

---

### 1.6 Docker Compose

Docker Compose 是**批量管理容器的工具**。一个 `docker-compose.yml` 文件定义所有服务，一条命令操控全部。

```yaml
version: '3'
services:
  app:
    build: .
    ports: ["8000:8000"]
    depends_on: [redis, db]
  redis:
    image: redis:7-alpine
  db:
    image: postgres:15
```

```bash
docker-compose up -d      # 一键启动全部服务
docker-compose down       # 一键停止+删除
docker-compose logs -f    # 看所有服务日志
```

---

## 二、PostgreSQL 核心概念

### 2.1 pgvector

PostgreSQL 的**向量扩展插件**，让数据库能存向量并做相似度搜索。

**不用 pgvector**：向量存 Chroma/Milvus，业务数据存 PostgreSQL，两套存储，数据同步麻烦。

**用了 pgvector**：一张表同时存商品信息和商品向量，一个库搞定。

```sql
CREATE EXTENSION vector;
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    embedding vector(1024)   -- 存 1024 维向量
);

-- 查最相似的 5 个商品
SELECT name FROM products
ORDER BY embedding <=> '[0.1, 0.3, ...]'::vector
LIMIT 5;
```

---

### 2.2 JSON vs JSONB

| | JSON | JSONB |
|------|------|------|
| 存储方式 | 原样存文本，每次查都要解析 | 存二进制，查时不用解析 |
| 查询速度 | 慢 | 快 |
| 索引 | 不支持 | 支持 GIN 索引 |
| 写入速度 | 快（不解析直接存） | 稍慢（要先转二进制） |
| 空格/顺序 | 保留 | 不保留 |

**记法**：JSONB 的 B = **B**etter，多一道转换，换来查询快+能建索引。实际开发中绝大多数场景用 JSONB。

---

### 2.3 MVCC

**M**ulti-**V**ersion **C**oncurrency **C**ontrol，多版本并发控制。

**解决的问题**：多个人同时读写同一行数据，怎么不互相阻塞？

**原理**：数据不直接覆盖，保留多个版本。每个事务看到的是自己"开始那一刻"的数据快照。

```
时间线：
张三 开始事务 ──────────── 读到余额=100 ── 提交
李四          转账 100→200 ── 提交
张三 仍然看到余额=100（他的快照不变）← 这就是 MVCC
```

**一句话**：读写不互锁，读的人不用等写的人，写的人也不用等读的人。PostgreSQL 高并发场景下比 MySQL 更丝滑。

---

## 三、Redis 五大数据类型

### 3.1 String（字符串）

最基础的类型，key-value 一对。

```bash
SET name "张三"
GET name              # "张三"
SET count 100
INCR count            # 101（原子自增，高并发下计数不出错）
SETEX token 3600 "abc123"  # 设值+过期时间
```

**场景**：缓存热点问答对、分布式锁、计数器。

---

### 3.2 Hash（哈希）

key 下面挂一组 field-value 对，像个小字典。

```bash
HSET user:1001 name "张三" age 25 city "南京"
HGET user:1001 name       # "张三"
HGETALL user:1001         # 拿全部字段
```

**特点**：适合存对象，每个 field 可以单独读写，不用整个序列化。

**场景**：语音陪伴 Agent 存用户长期记忆。每个用户一个 Hash，field 是记忆片段，value 是记忆详情。

---

### 3.3 List（列表）

有序的字符串列表，底层是双向链表，**两头操作快**。

```bash
LPUSH messages "消息1"    # 左边插入
RPUSH messages "消息2"    # 右边插入
LRANGE messages 0 -1      # 查看全部
```

**场景**：消息队列（简单版）、最近聊天记录。

---

### 3.4 Set（集合）

无序、不重复的字符串集合，支持交并差集运算。

```bash
SADD tags "RAG" "Agent" "Docker"
SINTER set1 set2          # 交集
SUNION set1 set2          # 并集
```

**场景**：标签系统、共同好友、去重统计。

---

### 3.5 Sorted Set（有序集合）

Set 的升级版，每个元素带一个**分数(score)**，按分数自动排序。

```bash
ZADD leaderboard 100 "张三" 85 "李四" 92 "王五"
ZREVRANGE leaderboard 0 -1 WITHSCORES  # 降序+显示分数
```

**场景**：排行榜、热门问题 Top N、带权重的优先队列。

---

### 一张表总结

| 类型 | 一句话 | 类比 | 关键命令 |
|------|--------|------|----------|
| String | key-value | 变量 | GET/SET/INCR |
| Hash | key 下多个 field-value | Python dict | HSET/HGET/HGETALL |
| List | 有序列表 | 双向链表 | LPUSH/RPUSH/LPOP/RPOP |
| Set | 无序不重复 | Python set | SADD/SMEMBERS/SINTER |
| Sorted Set | 带分数排序的 Set | 排行榜 | ZADD/ZRANGE/ZREVRANGE |

---

## 四、SSE 流式响应

### 4.1 是什么

SSE（Server-Sent Events）是一种**服务器向客户端单向推送数据**的技术。客户端发一个 HTTP 请求，服务器一直保持连接，有数据就推过来。

```
普通 HTTP：  客户端问 → 服务器答 → 连接关闭
SSE：        客户端问 → 服务器答一点 → 再答一点 → ... → 关闭
```

### 4.2 SSE vs WebSocket

| | SSE | WebSocket |
|------|------|-----------|
| 方向 | 单向（服务器→客户端） | 双向 |
| 协议 | HTTP | 独立协议 ws:// |
| 断线重连 | 浏览器自动重连 | 需自己实现 |
| 实现复杂度 | 简单 | 复杂 |

**为什么 RAG 用 SSE？** LLM 生成 token 是单向的，服务器推给前端即可，SSE 刚好够用且更简单。

### 4.3 前端写法（EventSource）

EventSource 是浏览器内置的 SSE 客户端 API。

```javascript
const es = new EventSource('http://localhost:8000/chat?query=什么是RAG');

es.onmessage = (event) => {
  setAnswer(prev => prev + event.data);  // 逐 token 拼接
};

es.addEventListener('done', () => {
  es.close();  // 流结束，断开连接
});
```

### 4.4 后端写法（FastAPI + StreamingResponse）

FastAPI 是 Python 的现代异步 Web 框架，`StreamingResponse` 是其流式响应类。

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

async def generate_answer(query: str):
    answer = "RAG 是检索增强生成技术..."
    for char in answer:
        yield f"data: {char}\n\n"       # SSE 格式
        await asyncio.sleep(0.05)

@app.get("/chat")
async def chat(query: str):
    return StreamingResponse(
        generate_answer(query),
        media_type="text/event-stream"   # 告诉浏览器这是 SSE
    )
```

**SSE 数据格式**：`data: 内容\n\n`，每条消息以 `data:` 开头，两个换行结尾。

### 4.5 首字延迟控制

首字延迟 = 用户发问 → 屏幕上出现第一个字的时间。

```
总延迟 = 检索耗时(~200ms) + Prompt构建(~50ms) + LLM首token(~500ms-1s)
```

**优化手段**：HNSW 索引实现毫秒级向量检索、提前拼接 Prompt 模板、选推理快的模型。

---

## 五、HNSW 快速检索算法

**H**ierarchical **N**avigable **S**mall **W**orld，分层可导航小世界图。

**问题**：100 万个向量，怎么快速找到最相似的 Top-3？

**暴力法**：全部算一遍相似度 → O(n)，太慢。

**HNSW 思路**：提前建好导航图，检索时顺着图快速走到目标区域。

```
类比：在南京找火锅店

暴力法 = 每家店都进去看一遍
HNSW  = 先看哪个区 → 再看哪条街 → 再看哪家店（三层导航）
```

**分层结构**：

```
第2层（最稀疏）：几个关键节点，快速定位大方向
第1层（中等）：更多节点，缩小范围
第0层（最密）：所有节点，精确找到最近邻
```

**一句话**：HNSW 就是给向量建了"高德地图"，检索时按导航走，复杂度 O(log n)。Milvus 底层就用 HNSW 索引。

---

## 六、Hybrid Search 混合检索

### 6.1 为什么需要混合检索

**纯向量检索的弱点**：对精确关键词不敏感，搜"iPhone 15 Pro Max 256G"可能返回 iPhone 15 评测（语义相似但没价格）。

**纯关键词检索的弱点**：只匹配字面，搜"苹果手机怎么录屏"可能返回"苹果派的做法"。

**Hybrid Search = 向量检索 + 关键词检索，两者互补。**

### 6.2 两路并行检索

```
用户提问
  ├──→ 向量检索（语义理解）──→ 用 Embedding 做相似度
  └──→ 关键词检索（字面匹配）→ 用 BM25 算法打分
                              ↓
                         RRF 融合排序
                              ↓
                         最终结果
```

**BM25**：经典关键词打分算法。词出现次数越多分越高（但会饱和），词越稀有权重越大，文档越短匹配度越高。

### 6.3 RRF 融合

RRF（Reciprocal Rank Fusion）：不关心原始分数，只看排名。

```
向量检索排名：1.评测  2.选购指南  3.价格表
关键词排名：  1.价格表  2.规格  3.促销

RRF 公式：score = 1 / (60 + rank)

价格表：两路都排前列 → 融合后冲第一
```

### 6.4 面试话术

> 纯向量检索对专有名词、型号、数字等不敏感。我加了 BM25 关键词检索做互补——关键词能精确匹配到型号和价格，向量能理解语义相似的表述。两个结果用 RRF 算法融合，兼顾了精确匹配和语义理解，召回率提升明显。

---

## 七、快速复习清单

| 类别 | 考点 | 关键词 |
|------|------|--------|
| Docker | 启动容器 | `run -d -p --name` |
| Docker | 进入容器 | `exec -it` |
| Docker | 查看日志 | `logs -f / --tail` |
| Docker | Compose | `up -d / down / logs -f` |
| PostgreSQL | pgvector | 向量扩展，存向量+查相似 |
| PostgreSQL | JSONB | 二进制JSON，查询快，支持索引 |
| PostgreSQL | MVCC | 多版本并发，读写不互锁 |
| Redis | String | 缓存，GET/SET/INCR |
| Redis | Hash | 存对象，HSET/HGET |
| Redis | List | 队列，LPUSH/RPUSH |
| Redis | Set | 去重集合，SADD/SINTER |
| Redis | Sorted Set | 排行榜，ZADD/ZRANGE |
| SSE | 流式响应 | EventSource + StreamingResponse |
| HNSW | 快速检索 | 分层导航图，O(log n) |
| Hybrid Search | 混合检索 | 向量+BM25，RRF融合 |