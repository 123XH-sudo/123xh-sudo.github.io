---
layout: single
title: "RAG 学习笔记：系统集成与部署 — 聊天窗口、API 代理与知识库同步"
date: 2026-08-12 00:00:00 +0800
categories: 
  - 学习笔记
tags:
  - RAG
  - Dify
  - Cloudflare Workers
  - GitHub Actions
  - Jekyll
  - 系统集成

toc: true
toc_sticky: true
---

## 一、前情回顾

前三篇笔记完成了 RAG 检索策略的学习——相似度计算、查询优化、多轮检索与回退。现在整个 RAG 系统的"内功"已经就位，但还差最后一步：**让用户真正用上**。

阶段六的目标非常明确：

1. 在博客网站嵌入一个聊天窗口，用户可以直接提问
2. 保护 API Key，不能暴露在前端代码里
3. 每次推送新博客到 GitHub，知识库自动同步更新

三个目标，三件事。

---

## 二、嵌入聊天窗口

### 2.1 技术选型

我的博客是 Jekyll 静态页面，部署在 GitHub Pages 上。Dify 提供了 Chat API，支持流式返回（SSE），前端只需要调用这个 API 就能实现对话。

核心方案：

- 前端：纯 HTML + CSS + JS，做成一个 `chat-widget.html`，通过 Jekyll 的 `{% raw %}{% include %}{% endraw %}` 引入
- 通信：通过 Fetch API 调用 Dify Chat API，流式读取 SSE 响应
- 样式：固定在页面右下角的悬浮窗口，点击展开/收起

### 2.2 流式响应与 SSE 解析

Dify 的 Chat API 有两种模式：`blocking`（一次性返回）和 `streaming`（逐字流式返回）。聊天场景当然选流式，体验更好。

SSE 的格式是：

```
data: {"event":"message","answer":"Docker","conversation_id":"xxx"}

data: {"event":"message","answer":" 是","conversation_id":"xxx"}

data: {"event":"message_end","conversation_id":"xxx"}
```

每一行 `data: {...}` 携带一个增量片段。前端用 `response.body.getReader()` 逐块读取，按换行分割，解析 JSON 后拼接 `answer` 字段。

### 2.3 遇到的坑：流式响应显示空白

这是整个阶段六最坑的问题——聊天窗口能打开、能连接、能看到网络请求返回 200，但助手回复就是空的。

排查过程：

1. 先怀疑是 SSE 解析问题，检查了 `data:` 前缀的判断逻辑，没问题
2. 用浏览器 DevTools 看网络请求，响应体确实有内容
3. 最后发现是我写的 JS 里，`answerText = data.answer` 用的是**赋值**而不是**拼接**

Dify 的流式 API 每次只返回一个增量片段（比如第一次返回 `"Docker"`，第二次返回 `" 是"`），如果用 `=` 赋值，每次都会覆盖前一次的内容，最终只显示最后一个片段。正确的做法是 `answerText += data.answer`。

```javascript
// 错误：每次覆盖
answerText = data.answer;

// 正确：逐段拼接
answerText += data.answer;
```

一个 `+` 号 debug 了半小时。

### 2.4 样式调整

第一版样式非常简陋，就是一个白框框。后来改成了渐变紫色主题，加了在线状态指示点、打字动画、Markdown 渲染、移动端适配。虽然不是什么核心技术，但用户体验确实好了一大截。

---

## 三、Cloudflare Worker 代理

### 3.1 为什么需要代理

Dify Chat API 的调用需要在请求头里带上 `Authorization: Bearer <api-key>`。如果直接写在博客前端 JS 里，任何人打开 F12 就能看到你的 API Key，然后滥用你的额度。

对于静态博客，没有后端服务器，无法做服务端转发。常见的解决方案：

| 方案 | 可行性 |
|------|--------|
| 直接写在前端 | 不安全，API Key 暴露 |
| 自建 Nginx 反向代理 | 需要服务器，成本高 |
| Vercel / Netlify Functions | 可以，但博客已在 GitHub Pages |
| Cloudflare Workers | 免费额度 10万次/天，完美 |

### 3.2 Workers 实现

Worker 代码很简单，总共不到 70 行：

1. 接收前端发来的 POST 请求（不包含 API Key）
2. 拼接上 API Key，转发到 Dify 的 `/v1/chat-messages`
3. 把 Dify 的 SSE 流式响应原样返回给前端

```javascript
const DIFY_API_URL = 'https://api.dify.ai/v1/chat-messages';
const DIFY_API_KEY = 'app-xxx';  // 存在 Worker 里，前端看不到

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      // 处理 CORS 预检
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      });
    }
    
    const body = await request.json();
    const response = await fetch(DIFY_API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${DIFY_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ...body, response_mode: 'streaming' })
    });
    
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
};
```

前端只需要把请求发到 Workers 地址即可：

```javascript
const PROXY_URL = 'https://dify-proxy.xxx.workers.dev';
// 原来的 API Key 不需要了，Worker 会自动加上
```

部署后，记得把 `cloudflare-worker.js` 加入 `.gitignore`，防止 API Key 被提交到 GitHub。

---

## 四、GitHub Actions 自动同步知识库

### 4.1 目标

每次推送新博客到 GitHub，自动把 `_posts/` 下的变更文件上传到 Dify 知识库，不需要手动操作。

### 4.2 触发条件

```yaml
on:
  push:
    branches: [main]
    paths:
      - '_posts/**.md'
```

只有 `main` 分支上 `_posts/` 目录下的 `.md` 文件变更时才触发，避免无关推送浪费资源。

### 4.3 变更检测

{% raw %}
```bash
git diff --name-only ${{ github.event.before }} ${{ github.event.after }} -- _posts/
```
{% endraw %}

用 `git diff` 对比两次 commit 之间的文件差异，只提取 `_posts/` 下的文件。这样每次同步只上传真正变更的文件，不会重复上传。

### 4.4 上传到 Dify

Dify 提供了知识库 API 的 `create-by-file` 接口，直接上传 Markdown 文件即可，Dify 会自动分段和索引。

{% raw %}
```bash
curl -X POST "https://api.dify.ai/v1/datasets/$DATASET_ID/document/create-by-file" \
  -H "Authorization: Bearer ${{ secrets.DIFY_API_KEY }}" \
  -F "file=@$file" \
  -F "indexing_technique=high_quality"
```
{% endraw %}

API Key 通过 GitHub Secrets 管理，不会暴露在 workflow 文件里。

### 4.5 遇到的坑

**API Key 权限问题**：一开始用的 `app-xxx` 开头的 API Key 是 Chat API 的 Key，没有数据集操作的权限。Dify 有两类 API Key：

| Key 类型 | 前缀 | 用途 |
|----------|------|------|
| 应用 API Key | `app-` | 调用 Chat/Workflow API |
| 数据集 API Key | `dataset-` | 操作知识库文档 |

知识库同步需要 `dataset-` 开头的 Key，在 Dify 知识库设置页面单独生成。

**TLS 握手失败**：推送代码时偶尔遇到 `gnutls_handshake() failed` 错误，是网络问题，重试几次就好了。

---

## 五、个人思考

学之前，我对"系统集成"的理解就是"把东西拼在一起"。实际做完才发现，从拼在一起到真正能用，中间隔着一堆细节问题。

**关于 API Key 安全**：以前觉得 API Key 安全是后端的事，静态博客没后端就没办法。Cloudflare Workers 这个方案让我意识到，Serverless 函数就是静态站点的"后端"，不需要买服务器也能做服务端转发。

**关于流式响应**：`=` 和 `+=` 的 bug 花了我半小时，但这个问题在阻塞模式下根本不会出现。流式传输的调试比普通请求复杂，因为响应是分段的，浏览器 DevTools 也不方便直接看。

**关于自动化**：手动上传 5 篇博客到知识库只需要 2 分钟，但以后博客会越来越多，每次手动上传就是重复劳动。GitHub Actions 的自动化虽然前期花时间配置，但长期来看值得。而且这个 workflow 文件本身也是博客的一部分，可以复用。

**关于规模**：和阶段四的实验一样，很多东西在 10 篇文章的规模下看不出差别。但知识库同步这个需求，恰恰是规模越大越有价值——50 篇、100 篇博客的时候，手动同步根本不现实。

---

## 六、总结

阶段六完成了三件事：

1. **聊天窗口**：嵌入博客，流式对话，用户可以直接提问
2. **API 代理**：Cloudflare Worker 隐藏 API Key，前端安全
3. **自动同步**：GitHub Actions 监听推送，自动更新知识库

整个 RAG 系统的学习到这里就闭环了：从向量数据库、检索策略、查询优化，到生成模块，再到系统集成——从理论到实践，从零到一，搭建了一个完整的个人博客 RAG 问答系统。

目前系统规模很小（10 篇文章，约 48 个 chunk），很多优化手段的效果还看不出来。但架构和流程是正确的，等博客内容积累起来，这套系统的价值会越来越明显。

> 本文写于 2026 年 8 月 12 日，整个 RAG 系统学习项目正式完结。
