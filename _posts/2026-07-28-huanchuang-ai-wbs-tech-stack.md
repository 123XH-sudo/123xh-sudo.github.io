---
layout: post
title: "焕创AI 系统工作包分解与技术栈方案"
date: 2026-07-28 12:00:00 +0800
categories: 技术方案
tags: [焕创AI, WBS, 技术栈, 重构, TypeScript, NestJS, React]
---

# 焕创AI 电商图像生产系统 — 工作包分解与重写技术方案

> 版本：v2.0 | 日期：2026-07-28 | 当前版本：2026.07.18.opsagent-closeup-productlock

---

## 一、系统概述

焕创AI 是一套面向电商运营的 **AI 图像/视频生产桌面应用**，核心功能包括：

- 电商产品图、场景图、详情图、A+横幅图的 AI 生成
- 多模型/多 Provider 统一调度（GPT-Image-2、Gemini、ModelScope、RunningHub、火山引擎、即梦等）
- 无限画布工作台（节点式工作流编排）
- CODEX AI Agent 全自动协作出图
- 视频生成（Veo/Sora/Seedance/通义万相）
- 图片高清放大、角度控制、提示词反推
- GPT 对话聊天
- 项目/画布管理、素材库、快捷提示词库
- 客户端认证、API Key 管理、自动更新

**当前技术架构**：

- 后端：Python FastAPI（单文件 `main.py` 约 17,000 行）
- 前端：原生 HTML + JS + CSS（无框架，`canvas.js` 约 24,000 行）
- 桌面壳：pywebview（Windows EdgeChromium 后端）/ 浏览器回退
- 存储：纯文件系统 + JSON（无数据库）
- 打包：Nuitka 单文件编译

---

## 二、技术选型决策

### 2.1 选型判断标准

**核心决策依据**：以现有 Codex agent 的依赖复杂度、沙箱实现难度为核心判断标准。

### 2.2 Codex Agent 依赖分析

| 依赖类型 | 复杂度 | 说明 |
|----------|--------|------|
| HTTP API 通信 | 低 | 18 个 REST 端点，标准 JSON 交互 |
| 规则文件同步 | 低 | Markdown + JSON 文件 |
| 会话状态管理 | 低 | JSON 文件存储 |
| 系统级依赖 | 无 | 不涉及注册表、COM、驱动 |

**结论**：Codex 规则引擎是语言无关的，NestJS 完全可以实现相同的 API 接口和规则解析逻辑。

### 2.3 最终选型

**方案：前后端分离网页形式 + Electron 可选桌面壳**

| 层次 | 技术选型 | 理由 |
|------|----------|------|
| 前端框架 | **React 18 + TypeScript** | 组件化、生态成熟 |
| 前端构建 | **Vite** | 极速 HMR、开箱即用 |
| 前端状态 | **Zustand** | 轻量、TS 友好 |
| 画布引擎 | **React Flow** | 成熟节点图库 |
| 图片编辑 | **Fabric.js** | 功能全面 |
| 后端框架 | **NestJS + TypeScript** | 会议明确要求 |
| AI 通信 | **Langchain (JS)** | 会议明确要求 |
| 数据库 | **PostgreSQL + TypeORM** | 结构化存储 |
| 任务队列 | **Bull + Redis** | 持久化、重试 |
| 实时通信 | **Socket.IO** | 自动重连 |
| 桌面壳 | **Electron** | 会议明确要求 |
| 密钥存储 | **keytar** | 跨平台替代 DPAPI |
| 图像处理 | **Sharp** | 性能 10x 优于 Pillow |
| 国际化 | **react-i18next** | 成熟方案 |

---

## 三、工作包分解结构（WBS）

### Level 1 — 7 大工作包

| 编号 | 工作包名称 | 说明 |
|------|-----------|------|
| WP1 | 核心基础设施 | 服务器、路由、中间件、WebSocket、存储、配置 |
| WP2 | 图像生成引擎 | 所有图片生成通道的统一调度与执行 |
| WP3 | 视频生成引擎 | 所有视频生成通道的统一调度与执行 |
| WP4 | 画布工作台 | 无限画布、节点系统、连线、项目管理 |
| WP5 | AI 对话与工具 | GPT 聊天、LLM 辅助、提示词反推、图片搜索 |
| WP6 | CODEX 联动系统 | AI Agent 全自动协作出图管线 |
| WP7 | 客户端与发布 | 桌面壳、认证、打包、自动更新、i18n |

---

### WP1 核心基础设施

**WP1.1** 应用框架与路由
- 实现方案：NestJS 模块化架构
- 技术选型：**NestJS + TypeScript**
- 理由：会议明确要求，模块化天然支持分层

**WP1.2** WebSocket 实时通信
- 实现方案：Socket.IO Gateway
- 技术选型：**@nestjs/websockets + Socket.IO**
- 理由：自动重连、房间管理、NestJS 原生集成

**WP1.3** 全局配置管理
- 实现方案：ConfigModule + .env
- 技术选型：**@nestjs/config**
- 理由：环境变量注入、类型安全

**WP1.4** 文件存储层
- 实现方案：TypeORM + 文件系统
- 技术选型：**TypeORM + fs/promises**
- 理由：结构化数据走DB，文件走文件系统

**WP1.5** 运行时目录管理
- 实现方案：PathService
- 技术选型：**Node.js path + app.getPath()**
- 理由：Electron 提供标准路径API

**WP1.6** 认证中间件
- 实现方案：AuthGuard
- 技术选型：**@nestjs/passport + JWT**
- 理由：标准化认证流程

**WP1.7** 机器指纹绑定
- 实现方案：Crypto模块
- 技术选型：**Node.js crypto (HMAC-SHA256)**
- 理由：替代Python hmac，功能等价

**WP1.8** 同源检查
- 实现方案：CorsMiddleware
- 技术选型：**@nestjs/common CorsOptions**
- 理由：框架内置支持

**WP1.9** 文件上传/下载/代理
- 实现方案：Multer + Stream
- 技术选型：**@nestjs/platform-express Multer**
- 理由：成熟方案，支持大文件

**WP1.10** 自动更新系统
- 实现方案：electron-updater
- 技术选型：**electron-updater (Squirrel)**
- 理由：Electron 生态标准方案

---

### WP2 图像生成引擎

**WP2.1** 在线图片生成统一调度
- 实现方案：Provider 适配器模式
- 技术选型：**Langchain + 自定义 Provider**
- 理由：会议明确要求 Langchain 统一封装

**WP2.1.1** GPT-Image-2 生成
- 实现方案：OpenAI Provider
- 技术选型：**Langchain OpenAI Integration**

**WP2.1.2** GPT-Image-2 参考图编辑
- 实现方案：OpenAI Provider + Canvas Prep
- 技术选型：**Langchain + Sharp**

**WP2.1.3** Gemini 图片生成
- 实现方案：Custom Provider
- 技术选型：**Langchain Custom LLM Wrapper**

**WP2.1.4** ModelScope 图片生成
- 实现方案：Custom Provider
- 技术选型：**Langchain Custom LLM Wrapper**

**WP2.1.5** RunningHub 云端生成
- 实现方案：Custom Provider
- 技术选型：**HTTP Client (axios)**

**WP2.1.6** 火山引擎/OpenRouter/KIE
- 实现方案：Custom Provider
- 技术选型：**Langchain OpenAI Compatible**

**WP2.1.7** Provider 熔断器
- 实现方案：Circuit Breaker
- 技术选型：**opossum**

**WP2.1.8** 并发信号量控制
- 实现方案：Semaphore
- 技术选型：**async-mutex / p-limit**

**WP2.2** ComfyUI 本地生成
- 实现方案：HTTP Client + Queue
- 技术选型：**axios + Bull Queue**

**WP2.2.1** ComfyUI 后端连接管理
- 实现方案：Connection Pool
- 技术选型：**axios + 自定义连接池**

**WP2.2.2** 工作流提交与轮询
- 实现方案：Bull Job + Polling
- 技术选型：**Bull Queue + setInterval**

**WP2.2.3** ComfyUI 实例管理
- 实现方案：CRUD + Health Check
- 技术选型：**TypeORM Entity + axios**

**WP2.2.4** 工作流管理
- 实现方案：File System + DB
- 技术选型：**fs/promises + TypeORM**

**WP2.3** 画布图片任务（异步队列）
- 实现方案：Bull Queue
- 技术选型：**Bull + Redis**

**WP2.3.1** 异步任务创建
- 实现方案：Bull Job Enqueue
- 技术选型：**queue.add()**

**WP2.3.2** 任务状态查询
- 实现方案：Bull Job Status
- 技术选型：**job.getState()**

**WP2.3.3** 任务取消/恢复
- 实现方案：Bull Job Control
- 技术选型：**job.discard() / job.promote()**

**WP2.4** 图片放大/高清
- 实现方案：Multi-Engine Pipeline
- 技术选型：**Sharp + 远程API**

**WP2.4.1** AI 放大（SeedVR2/ComfyUI）
- 实现方案：Pipeline Fallback
- 技术选型：**Bull Queue + axios**

**WP2.4.2** 美图 AI 超清
- 实现方案：HMAC Signature
- 技术选型：**Node.js crypto**

**WP2.4.3** 本地 PIL 放大
- 实现方案：Sharp 图像处理
- 技术选型：**sharp.resize() + .sharpen()**

**WP2.5** RunningHub 集成
- 实现方案：HTTP Client + Queue
- 技术选型：**axios + Bull**

**WP2.5.1** AI 应用提交/查询
- 实现方案：REST API Client
- 技术选型：**axios + async/await**

**WP2.5.2** 工作流管理
- 实现方案：CRUD + Config
- 技术选型：**TypeORM + JSON Schema**

**WP2.5.3** 素材上传
- 实现方案：Multipart Upload
- 技术选型：**axios FormData**

**WP2.6** 角度控制
- 实现方案：Async Task + Polling
- 技术选型：**Bull Queue + WebSocket**

**WP2.6.1** ModelScope 角度生成
- 实现方案：Custom Provider
- 技术选型：**Langchain Custom Wrapper**

**WP2.6.2** 角度任务轮询
- 实现方案：WebSocket Push
- 技术选型：**Socket.IO emit**

**WP2.7** Provider 管理
- 实现方案：CRUD + Discovery
- 技术选型：**TypeORM + axios**

**WP2.7.1** Provider CRUD
- 实现方案：REST API
- 技术选型：**NestJS Controller + Service**

**WP2.7.2** 连接测试/协议探测
- 实现方案：Health Check
- 技术选型：**axios + timeout**

**WP2.7.3** 模型列表拉取
- 实现方案：API Discovery
- 技术选型：**axios + cache**

**WP2.7.4** Gemini 图片能力探测
- 实现方案：Capability Probe
- 技术选型：**axios + feature flag**

---

### WP3 视频生成引擎

**WP3.1** 视频生成统一入口
- 实现方案：Provider 适配器
- 技术选型：**Langchain Custom Provider**

**WP3.2** Veo 系列
- 实现方案：Google Provider
- 技术选型：**Langchain Google Integration**

**WP3.3** Sora-2
- 实现方案：OpenAI Provider
- 技术选型：**Langchain OpenAI Integration**

**WP3.4** 通义万相
- 实现方案：Custom Provider
- 技术选型：**Langchain Custom Wrapper**

**WP3.5** 豆包 Seedance
- 实现方案：Custom Provider
- 技术选型：**Langchain Custom Wrapper**

**WP3.6** 即梦
- 实现方案：CLI Wrapper
- 技术选型：**child_process.spawn()**

**WP3.7** APIMart / OpenAI 协议适配
- 实现方案：Protocol Adapter
- 技术选型：**Strategy Pattern**

**WP3.8** 首帧/尾帧/参考图/参考视频
- 实现方案：Multi-Input Handler
- 技术选型：**Multer + FFmpeg**

**WP3.9** 云视频上传
- 实现方案：Cloud Upload Service
- 技术选型：**axios + FormData**

**WP3.10** LTX Director 时间线
- 实现方案：Frontend Timeline
- 技术选型：**React + react-timeline-editor**

---

### WP4 画布工作台

**WP4.1** 画布 CRUD 与项目管理
- 实现方案：REST API + DB
- 技术选型：**NestJS + TypeORM**

**WP4.1.1** 画布创建/读取/保存/删除
- 实现方案：CRUD API
- 技术选型：**NestJS Controller + Service**

**WP4.1.2** 画布回收站
- 实现方案：Soft Delete
- 技术选型：**TypeORM @DeleteDateColumn**

**WP4.1.3** 画布元数据
- 实现方案：Lightweight Query
- 技术选型：**TypeORM select partial**

**WP4.1.4** 画布时间戳更新
- 实现方案：Touch API
- 技术选型：**TypeORM update**

**WP4.2** 节点系统
- 实现方案：React Flow
- 技术选型：**@xyflow/react**

**WP4.2.1 ~ WP4.2.9** 各节点类型（图片卡片/提示词/API生成/Output/循环/LLM/视频/RH/批处理）
- 实现方案：Custom Node
- 技术选型：**React Flow Custom Node**

**WP4.3** 画布交互
- 实现方案：React Flow Built-in
- 技术选型：**@xyflow/react**

**WP4.3.1** 无限画布平移/缩放
- 实现方案：Viewport Control
- 技术选型：**React Flow useViewport**

**WP4.3.2** 节点拖放/框选/连线
- 实现方案：Drag & Drop
- 技术选型：**React Flow DnD**

**WP4.3.3** 小地图导航
- 实现方案：MiniMap
- 技术选型：**React Flow MiniMap**

**WP4.3.4** 自动整理/对齐
- 实现方案：Layout Algorithm
- 技术选型：**dagre / elkjs**

**WP4.3.5** 图片拖放上传
- 实现方案：DnD + Upload
- 技术选型：**react-dropzone**

**WP4.4** 图片编辑
- 实现方案：Fabric.js
- 技术选型：**fabric.js**

**WP4.4.1** 裁剪
- 实现方案：Fabric Crop
- 技术选型：**fabric.js + react-cropper**

**WP4.4.2** 扩展（Outpaint）
- 实现方案：Fabric Outpaint
- 技术选型：**fabric.js + AI API**

**WP4.4.3** 遮罩/画笔
- 实现方案：Fabric Brush
- 技术选型：**fabric.js PencilBrush**

**WP4.4.4** 宫格切分
- 实现方案：Fabric Grid
- 技术选型：**fabric.js + custom logic**

**WP4.5** 画布资源管理
- 实现方案：File Service
- 技术选型：**NestJS + fs/promises**

**WP4.5.1** 资源检查
- 实现方案：Existence Check
- 技术选型：**fs.access()**

**WP4.5.2** 打包下载（ZIP）
- 实现方案：ZIP Generation
- 技术选型：**archiver**

**WP4.5.3** 本地保存
- 实现方案：File Save
- 技术选型：**fs/promises**

**WP4.5.4** 选择/打开保存文件夹
- 实现方案：Native Dialog
- 技术选型：**electron.dialog**

**WP4.5.5** 项目导出/导入
- 实现方案：ZIP Import/Export
- 技术选型：**archiver + extract-zip**

**WP4.5.6** 项目本地保存
- 实现方案：Folder Save
- 技术选型：**fs/promises**

**WP4.6** 多模式工作台
- 实现方案：Frontend State
- 技术选型：**Zustand + React**

**WP4.6.1** 简单模式
- 实现方案：Simplified UI
- 技术选型：**React Components**

**WP4.6.2** 专业模式
- 实现方案：Full Canvas
- 技术选型：**React Flow**

**WP4.6.3** 运营模式
- 实现方案：Design Preview
- 技术选型：**React + Custom Layout**

**WP4.7** 快捷提示词库
- 实现方案：CRUD API + DB
- 技术选型：**NestJS + TypeORM**

**WP4.7.1** 提示词库 CRUD
- 实现方案：REST API
- 技术选型：**NestJS Controller**

**WP4.7.2** 提示词模板
- 实现方案：Template System
- 技术选型：**JSON + Frontend**

**WP4.8** 素材库
- 实现方案：CRUD API + DB
- 技术选型：**NestJS + TypeORM**

**WP4.8.1** 分类管理
- 实现方案：Category CRUD
- 技术选型：**NestJS Controller**

**WP4.8.2** 条目管理
- 实现方案：Item CRUD
- 技术选型：**NestJS Controller**

**WP4.9** 智能画布
- 实现方案：Lightweight Canvas
- 技术选型：**React + Custom Canvas**

**WP4.9.1** 多引擎选择
- 实现方案：Engine Selector
- 技术选型：**React Select + Zustand**

**WP4.9.2** 图片/视频双模式
- 实现方案：Mode Toggle
- 技术选型：**React State**

**WP4.9.3** 资产库集成
- 实现方案：Asset Panel
- 技术选型：**React Components**

**WP4.9.4** 全景预览
- 实现方案：360 Viewer
- 技术选型：**three.js + React**

**WP4.9.5** 分组导出
- 实现方案：Group Export
- 技术选型：**NestJS + archiver**

**WP4.10** 一键详情页
- 实现方案：Wizard UI
- 技术选型：**React Steps + AI API**

**WP4.10.1** 平台/尺寸/风格选择
- 实现方案：Config Form
- 技术选型：**React Form**

**WP4.10.2** AI 生成详情提示词
- 实现方案：LLM Chain
- 技术选型：**Langchain Chain**

**WP4.11** 历史记录
- 实现方案：Pagination API
- 技术选型：**NestJS + TypeORM**

**WP4.11.1** 生成历史
- 实现方案：History List
- 技术选型：**TypeORM find + paginate**

**WP4.11.2** 历史删除/批量操作
- 实现方案：Batch Delete
- 技术选型：**TypeORM delete**

---

### WP5 AI 对话与工具

**WP5.1** GPT 对话聊天
- 实现方案：Chat Service
- 技术选型：**Langchain + NestJS**

**WP5.1.1** 文本聊天
- 实现方案：LLM Chain
- 技术选型：**Langchain Conversation Chain**

**WP5.1.2** 流式聊天
- 实现方案：SSE Stream
- 技术选型：**@nestjs/event-emitter + SSE**

**WP5.1.3** 图像生成模式
- 实现方案：Multi-Mode
- 技术选型：**Langchain + Image Provider**

**WP5.1.4** 对话管理
- 实现方案：CRUD API
- 技术选型：**NestJS + TypeORM**

**WP5.1.5** 参考图上传
- 实现方案：File Upload
- 技术选型：**Multer + fs**

**WP5.2** 画布 LLM 辅助
- 实现方案：Vision LLM
- 技术选型：**Langchain Vision Model**

**WP5.2.1** 多模态 LLM 调用
- 实现方案：Vision API
- 技术选型：**Langchain + GPT-4V/Gemini**

**WP5.2.2** 提示词辅助
- 实现方案：Prompt Helper
- 技术选型：**Langchain Chain**

**WP5.3** 提示词反推
- 实现方案：Reverse Prompt
- 技术选型：**Langchain + Vision**

**WP5.3.1** 图片→提示词
- 实现方案：Image-to-Prompt
- 技术选型：**Langchain Vision Chain**

**WP5.4** 参考图工具
- 实现方案：Web Scraper + Search
- 技术选型：**axios + cheerio**

**WP5.4.1** 链接预览
- 实现方案：Link Preview
- 技术选型：**axios + cheerio**

**WP5.4.2** Bing 图片搜索
- 实现方案：Image Search
- 技术选型：**axios + HTML parsing**

**WP5.5** 图像增强工具
- 实现方案：Multi-Engine
- 技术选型：**Sharp + Remote API**

**WP5.5.1** 本地增强
- 实现方案：Local Processing
- 技术选型：**sharp + custom pipeline**

**WP5.5.2** 云端增强
- 实现方案：Cloud API
- 技术选型：**axios + ModelScope**

**WP5.6** FLUX Klein 合成终端
- 实现方案：Multi-Input UI
- 技术选型：**React + Langchain**

**WP5.6.1** 三图输入合成
- 实现方案：Multi-Image Input
- 技术选型：**React Dropzone + Langchain**

**WP5.6.2** LoRA 集成
- 实现方案：LoRA Config
- 技术选型：**TypeORM + JSON**

---

### WP6 CODEX 联动系统

**WP6.1** 会话管理
- 实现方案：Session Service
- 技术选型：**NestJS + TypeORM**

**WP6.1.1** Link 会话创建/更新
- 实现方案：Session CRUD
- 技术选型：**TypeORM Entity**

**WP6.1.2** 会话完成/关闭
- 实现方案：Session Complete
- 技术选型：**TypeORM update + cleanup**

**WP6.1.3** 会话状态查询
- 实现方案：Session Query
- 技术选型：**TypeORM find**

**WP6.1.4** 活跃信标管理
- 实现方案：Beacon File
- 技术选型：**fs/promises + JSON**

**WP6.2** Bootstrap 引导
- 实现方案：Rule Installer
- 技术选型：**fs/promises + crypto**

**WP6.2.1** 规则包安装/验证/修复
- 实现方案：Rule Sync
- 技术选型：**fs + SHA256 (crypto)**

**WP6.2.2** SKILL 完整性检查
- 实现方案：Integrity Check
- 技术选型：**crypto.createHash('sha256')**

**WP6.2.3** 版本门控
- 实现方案：Version Gate
- 技术选型：**semver**

**WP6.3** 需求收件箱
- 实现方案：Requirement Inbox
- 技术选型：**NestJS + TypeORM**

**WP6.3.1** 需求行提交
- 实现方案：Batch Create
- 技术选型：**TypeORM save**

**WP6.3.2** 需求行查询
- 实现方案：Query API
- 技术选型：**TypeORM find**

**WP6.3.3** 参考图绑定
- 实现方案：Reference Binding
- 技术选型：**TypeORM relation**

**WP6.4** 行级 Agent 跟踪矩阵
- 实现方案：Row Matrix
- 技术选型：**NestJS + TypeORM**

**WP6.4.1** Row Agent 状态管理
- 实现方案：State Management
- 技术选型：**TypeORM Entity**

**WP6.4.2** 字段合并保护
- 实现方案：Merge Protection
- 技术选型：**Custom Logic**

**WP6.5** 命令队列
- 实现方案：Command Queue
- 技术选型：**Bull Queue**

**WP6.5.1** 命令提交
- 实现方案：Command Enqueue
- 技术选型：**queue.add()**

**WP6.5.2** 命令确认
- 实现方案：Command ACK
- 技术选型：**job.update()**

**WP6.5.3** 命令轮询
- 实现方案：Command Polling
- 技术选型：**WebSocket + Bull**

**WP6.6** Prompt Gate 与 QC
- 实现方案：Validation Pipeline
- 技术选型：**NestJS Pipes + Custom Validators**

**WP6.6.1** 产品锁验证
- 实现方案：Product Lock Check
- 技术选型：**Custom Validator**

**WP6.6.2** 比例匹配验证
- 实现方案：Ratio Check
- 技术选型：**Custom Validator**

**WP6.6.3** 显示文本泄漏检测
- 实现方案：Text Leak Check
- 技术选型：**Regex + Custom Validator**

**WP6.6.4** 角色引用分离
- 实现方案：Reference Separation
- 技术选型：**Custom Validator**

**WP6.6.5** 递归提示词检测
- 实现方案：Recursion Check
- 技术选型：**Custom Validator**

**WP6.7** Codex 上下文
- 实现方案：Context Service
- 技术选型：**NestJS Service**

**WP6.7.1** 上下文生成
- 实现方案：Context API
- 技术选型：**JSON Generation**

**WP6.7.2** 编码健康检查
- 实现方案：Encoding Check
- 技术选型：**iconv-lite**

---

### WP7 客户端与发布

**WP7.1** 桌面客户端
- 实现方案：Electron Shell
- 技术选型：**Electron + electron-builder**

**WP7.1.1** 源代码模式启动器
- 实现方案：Dev Mode
- 技术选型：**electron + vite**

**WP7.1.2** 编译模式启动器
- 实现方案：Prod Mode
- 技术选型：**electron-builder**

**WP7.1.3** 网页端入口
- 实现方案：Web Mode
- 技术选型：**Browser fallback**

**WP7.1.4** 单实例检测
- 实现方案：Single Instance
- 技术选型：**electron.app.requestSingleInstanceLock()**

**WP7.1.5** Windows 品牌化
- 实现方案：Branding
- 技术选型：**electron.app.setAppUserModelId()**

**WP7.2** 客户端认证
- 实现方案：Auth Service
- 技术选型：**NestJS + keytar**

**WP7.2.1** API Key 验证
- 实现方案：Key Validation
- 技术选型：**axios + gateway API**

**WP7.2.2** 密钥加密存储
- 实现方案：Secure Storage
- 技术选型：**keytar**

**WP7.2.3** 解锁/换 Key/登出
- 实现方案：Auth Lifecycle
- 技术选型：**NestJS Controller**

**WP7.2.4** Gateway-Only 模式
- 实现方案：Gateway Mode
- 技术选型：**Config Flag**

**WP7.3** API 账户管理
- 实现方案：Account Service
- 技术选型：**NestJS + TypeORM**

**WP7.3.1** 多账户管理
- 实现方案：Account CRUD
- 技术选型：**TypeORM Entity**

**WP7.3.2** 积分查看/刷新
- 实现方案：Usage Query
- 技术选型：**axios + provider API**

**WP7.4** 国际化（i18n）
- 实现方案：i18n Framework
- 技术选型：**react-i18next**

**WP7.4.1** 翻译框架
- 实现方案：i18n Setup
- 技术选型：**i18next + react-i18next**

**WP7.4.2** 页面翻译文件
- 实现方案：Translation Files
- 技术选型：**JSON + i18next**

**WP7.5** 构建与发布
- 实现方案：Build Pipeline
- 技术选型：**electron-builder + GitHub Actions**

**WP7.5.1** 前端 JS 混淆
- 实现方案：Code Obfuscation
- 技术选型：**javascript-obfuscator**

**WP7.5.2** 发布暂存准备
- 实现方案：Release Prep
- 技术选型：**Custom Script**

**WP7.5.3** Electron 打包
- 实现方案：Electron Build
- 技术选型：**electron-builder**

**WP7.5.4** 安装包生成
- 实现方案：Installer
- 技术选型：**electron-builder NSIS/DMG/deb**

**WP7.5.5** 发布验证
- 实现方案：Release Verify
- 技术选型：**Custom Script + SHA256**

**WP7.6** 主题系统
- 实现方案：Theme Manager
- 技术选型：**CSS Variables + Zustand**

**WP7.6.1** 深色/浅色切换
- 实现方案：Theme Toggle
- 技术选型：**CSS Variables**

**WP7.6.2** iframe 同步
- 实现方案：Theme Sync
- 技术选型：**postMessage**

**WP7.7** CODEX 规则包管理
- 实现方案：Rule Manager
- 技术选型：**NestJS Service**

**WP7.7.1** 规则模板安装
- 实现方案：Rule Install
- 技术选型：**fs/promises + crypto**

**WP7.7.2** 规则包同步
- 实现方案：Rule Sync
- 技术选型：**fs + SHA256**

**WP7.7.3** 预检工具
- 实现方案：Preflight Check
- 技术选型：**Custom Script**

**WP7.7.4** 画布上下文生成
- 实现方案：Context Gen
- 技术选型：**JSON Generation**

---

## 四、前端页面清单

| 页面 | 文件 | 功能定位 |
|------|------|---------|
| 主框架 | `index.html` | Shell 页面，左侧导航 + iframe 舞台 |
| 专业画布 | `canvas.html` | 核心工作台（简单/专业/运营三模式） |
| 智能画布 | `smart-canvas.html` | 轻量画布，多引擎选择 |
| GPT 对话 | `gpt-chat.html` | 聊天 + 图像生成 |
| API 设置 | `api-settings.html` | Provider 配置管理 |
| ComfyUI 设置 | `comfyui-settings.html` | 本地工作流配置 |
| Office API | `office-api.html` | API 账户与积分 |
| 图像增强 | `enhance.html` | 超分辨率放大 |
| 角度控制 | `angle.html` | 3D 角度调整（Three.js） |
| FLUX Klein | `klein.html` | 三图合成终端 |
| 在线生图 | `online.html` | 多 Provider 在线生成 |
| Z-Image | `zimage.html` | 统一艺术控制台 |

---

## 五、外部服务集成清单

| 服务 | 用途 | 协议 |
|------|------|------|
| 焕创 AI 网关 | 统一 API 代理 | OpenAI 兼容 / APIMart |
| OpenAI GPT-Image-2 | 图片生成/编辑 | OpenAI Images API |
| Google Gemini | 图片生成 | Gemini API |
| ModelScope | 图片生成 | OpenAI 兼容 |
| RunningHub | ComfyUI 云端工作流 | RunningHub 专有 API |
| 即梦 (Jimeng) | 图片/视频生成 | CLI |
| 火山引擎 (ARK) | 视频生成 | OpenAI 兼容 |
| OpenRouter | 多模型路由 | OpenAI 兼容 |
| KIE AI | 图片生成 | OpenAI 兼容 |
| 美图 (Meitu) | AI 超清放大 | 美图专有 API |
| ComfyUI (本地) | 本地图片生成 | ComfyUI HTTP API |
| GitHub | 自动更新 | GitHub API |
| Bing | 参考图搜索 | HTTP 抓取 |

---

## 六、当前架构痛点

| 问题 | 影响 |
|------|------|
| `main.py` 单文件 17,000 行 | 无法维护、无法协作开发 |
| `canvas.js` 单文件 24,000 行 | 前端逻辑耦合严重 |
| 无数据库，纯 JSON 文件 | 并发写入冲突、查询性能差 |
| 原生 HTML + JS 无框架 | 组件复用困难、状态管理混乱 |
| iframe 多页面架构 | 页面间通信困难、体验割裂 |
| pywebview 桌面壳 | 跨平台受限、调试困难 |
| 无前后端分离 | 无法独立部署、无法水平扩展 |
| Windows DPAPI 绑定 | 跨平台不可能 |

---

## 七、后端模块拆分建议

```
backend/
├── src/
│   ├── main.ts                 # NestJS 入口
│   ├── config/                 # 配置管理
│   ├── database/               # 数据库连接
│   ├── modules/                # 功能模块
│   │   ├── auth/               # 认证
│   │   ├── canvas/             # 画布管理
│   │   ├── image-gen/          # 图片生成
│   │   ├── video-gen/          # 视频生成
│   │   ├── chat/               # AI 对话
│   │   ├── providers/          # Provider 管理
│   │   ├── runninghub/         # RunningHub 集成
│   │   ├── codex/              # CODEX 联动
│   │   ├── assets/             # 素材/资源管理
│   │   ├── upscale/            # 图片放大
│   │   └── update/             # 自动更新
│   ├── services/               # 业务逻辑层
│   ├── repositories/           # 数据访问层
│   ├── entities/               # TypeORM 实体
│   ├── dto/                    # 数据传输对象
│   ├── guards/                 # 认证守卫
│   ├── interceptors/           # 拦截器
│   ├── pipes/                  # 验证管道
│   ── common/                 # 公共工具
├── test/
└── docker-compose.yml

frontend/
├── src/
│   ├── App.tsx
│   ├── pages/                  # 页面组件
│   │   ├── Canvas/             # 画布工作台
│   │   ├── Chat/               # GPT 对话
│   │   ├── Settings/           # API 设置
│   │   └── ...
│   ├── components/             # 通用组件
│   │   ├── Canvas/             # 画布相关组件
│   │   ├── NodeEditor/         # 节点编辑器
│   │   ├── ImagePreview/       # 图片预览
│   │   └── ...
│   ├── stores/                 # Zustand 状态
│   ├── services/               # API 调用层
│   ├── hooks/                  # 自定义 Hooks
│   ├── i18n/                   # 国际化
│   ── types/                  # TypeScript 类型
├── public/
└── package.json
```

---

## 八、关键数据模型（建议数据库表）

| 表名 | 说明 |
|------|------|
| `users` | 用户 |
| `api_keys` | API Key（加密存储） |
| `providers` | API Provider 配置 |
| `canvases` | 画布（含节点/连接/视口 JSON） |
| `canvas_nodes` | 画布节点 |
| `canvas_connections` | 节点连线 |
| `image_tasks` | 图片生成任务 |
| `video_tasks` | 视频生成任务 |
| `image_outputs` | 生成图片输出 |
| `video_outputs` | 生成视频输出 |
| `conversations` | 对话 |
| `messages` | 聊天消息 |
| `prompt_library` | 快捷提示词库 |
| `asset_categories` | 素材分类 |
| `assets` | 素材条目 |
| `runninghub_workflows` | RunningHub 工作流配置 |
| `comfyui_instances` | ComfyUI 实例 |
| `generation_history` | 生成历史 |
| `codex_sessions` | CODEX 联动会话 |
| `codex_requirements` | CODEX 需求行 |
| `codex_row_agents` | 行级 Agent 状态 |
| `update_backups` | 更新备份记录 |

---

## 九、开发阶段建议

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| **Phase 1** | 后端 NestJS 框架搭建 + 数据库设计 + Provider 适配器 | P0 |
| **Phase 2** | 前端 React 重构 + 画布引擎 + 基础图片生成 | P0 |
| **Phase 3** | 视频生成 + 图片放大 + RunningHub 集成 | P1 |
| **Phase 4** | CODEX 联动系统 + AI 对话 | P1 |
| **Phase 5** | 桌面壳（Electron） + 认证 + 自动更新 | P2 |
| **Phase 6** | i18n + 主题 + 素材库 + 历史管理 | P2 |
| **Phase 7** | 打包发布 + 性能优化 + 测试覆盖 | P3 |

---

## 十、总结

焕创AI 当前系统虽然结构混乱（单文件后端 17K 行 + 单文件前端 24K 行），但功能完整覆盖了电商 AI 图像生产的全链路。重写时应：

1. **保持功能一致**：按本 WBS 逐项对照，确保不遗漏
2. **模块化拆分**：后端按 NestJS 模块拆分，前端按页面/组件/store 拆分
3. **引入数据库**：PostgreSQL 替代 JSON 文件，解决并发和查询问题
4. **Provider 适配器模式**：统一接口、插拔式扩展新 Provider
5. **前后端分离**：独立部署、独立迭代
6. **任务队列**：Bull + Redis 替代内存队列，支持分布式和持久化
7. **全 TypeScript**：前后端统一语言，降低跨语言适配成本
8. **Langchain 统一 AI 层**：标准化 AI 调用，降低集成复杂度
