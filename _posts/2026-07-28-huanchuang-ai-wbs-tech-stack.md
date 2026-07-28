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
| 前端框架 | **React 18 + TypeScript** | 组件化、生态成熟、Langchain JS 集成好 |
| 前端构建 | **Vite** | 极速 HMR、开箱即用 TS |
| 前端状态 | **Zustand** | 轻量、TS 友好 |
| 画布引擎 | **React Flow (@xyflow/react)** | 成熟节点图库 |
| 图片编辑 | **Fabric.js** | 功能全面、社区大 |
| 后端框架 | **NestJS + TypeScript** | 会议明确要求、模块化、依赖注入 |
| AI 通信 | **Langchain (JS)** | 会议明确要求、统一封装 |
| 数据库 | **PostgreSQL + TypeORM** | 结构化存储、迁移支持 |
| 任务队列 | **Bull + Redis** | 持久化、重试、监控 |
| 实时通信 | **Socket.IO** | 自动重连、房间管理 |
| 桌面壳 | **Electron** | 会议明确要求、三端打包 |
| 密钥存储 | **keytar** | 跨平台替代 DPAPI |
| 图像处理 | **Sharp** | 性能 10x 优于 Pillow |
| 国际化 | **react-i18next** | 成熟方案 |

---

## 三、工作包分解结构（WBS）

### Level 1 — 系统模块（7 大工作包）

| 编号 | 工作包名称 | 说明 |
|------|-----------|------|
| WP1 | 核心基础设施 | 服务器启动、路由框架、中间件、WebSocket、存储、配置 |
| WP2 | 图像生成引擎 | 所有图片生成通道的统一调度与执行 |
| WP3 | 视频生成引擎 | 所有视频生成通道的统一调度与执行 |
| WP4 | 画布工作台 | 无限画布、节点系统、连线、项目管理 |
| WP5 | AI 对话与工具 | GPT 聊天、LLM 画布辅助、提示词反推、图片搜索 |
| WP6 | CODEX 联动系统 | AI Agent 全自动协作出图管线 |
| WP7 | 客户端与发布 | 桌面壳、认证、打包、自动更新、i18n |

---

### WP1 核心基础设施

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP1.1 | 应用框架与路由 | NestJS 模块化架构 | **NestJS + TypeScript** | 会议明确要求，模块化天然支持分层 |
| WP1.2 | WebSocket 实时通信 | Socket.IO Gateway | **@nestjs/websockets + Socket.IO** | 自动重连、房间管理、NestJS 原生集成 |
| WP1.3 | 全局配置管理 | ConfigModule + .env | **@nestjs/config** | 环境变量注入、类型安全 |
| WP1.4 | 文件存储层 | TypeORM + 文件系统 | **TypeORM + fs/promises** | 结构化数据走DB，文件走文件系统 |
| WP1.5 | 运行时目录管理 | PathService | **Node.js path + app.getPath()** | Electron 提供标准路径API |
| WP1.6 | 认证中间件 | AuthGuard | **@nestjs/passport + JWT** | 标准化认证流程 |
| WP1.7 | 机器指纹绑定 | Crypto模块 | **Node.js crypto (HMAC-SHA256)** | 替代Python hmac，功能等价 |
| WP1.8 | 同源检查 | CorsMiddleware | **@nestjs/common CorsOptions** | 框架内置支持 |
| WP1.9 | 文件上传/下载/代理 | Multer + Stream | **@nestjs/platform-express Multer** | 成熟方案，支持大文件 |
| WP1.10 | 自动更新系统 | electron-updater | **electron-updater (Squirrel)** | Electron 生态标准方案 |

---

### WP2 图像生成引擎

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP2.1 | 在线图片生成统一调度 | Provider 适配器模式 | **Langchain + 自定义 Provider** | 会议明确要求 Langchain 统一封装 |
| WP2.1.1 | GPT-Image-2 生成 | OpenAI Provider | **Langchain OpenAI Integration** | 官方支持，开箱即用 |
| WP2.1.2 | GPT-Image-2 参考图编辑 | OpenAI Provider + Canvas Prep | **Langchain + Sharp** | Sharp 替代 Pillow，性能更好 |
| WP2.1.3 | Gemini 图片生成 | Custom Provider | **Langchain Custom LLM Wrapper** | Gemini API 通过自定义适配器 |
| WP2.1.4 | ModelScope 图片生成 | Custom Provider | **Langchain Custom LLM Wrapper** | OpenAI 兼容协议，直接适配 |
| WP2.1.5 | RunningHub 云端生成 | Custom Provider | **HTTP Client (axios)** | 专有API，自定义实现 |
| WP2.1.6 | 火山引擎/OpenRouter/KIE | Custom Provider | **Langchain OpenAI Compatible** | OpenAI 兼容协议，统一适配 |
| WP2.1.7 | Provider 熔断器 | Circuit Breaker | **opossum** | 成熟的熔断器实现 |
| WP2.1.8 | 并发信号量控制 | Semaphore | **async-mutex / p-limit** | 轻量级并发控制 |
| WP2.2 | ComfyUI 本地生成 | HTTP Client + Queue | **axios + Bull Queue** | 异步任务队列替代内存字典 |
| WP2.2.1 | ComfyUI 后端连接管理 | Connection Pool | **axios + 自定义连接池** | 多实例负载均衡 |
| WP2.2.2 | 工作流提交与轮询 | Bull Job + Polling | **Bull Queue + setInterval** | 持久化任务，支持重试 |
| WP2.2.3 | ComfyUI 实例管理 | CRUD + Health Check | **TypeORM Entity + axios** | 数据库存储配置 |
| WP2.2.4 | 工作流管理 | File System + DB | **fs/promises + TypeORM** | JSON文件存储workflow定义 |
| WP2.3 | 画布图片任务（异步队列） | Bull Queue | **Bull + Redis** | 替代内存队列，支持分布式 |
| WP2.3.1 | 异步任务创建 | Bull Job Enqueue | **queue.add()** | 标准化任务入队 |
| WP2.3.2 | 任务状态查询 | Bull Job Status | **job.getState()** | 内置状态管理 |
| WP2.3.3 | 任务取消/恢复 | Bull Job Control | **job.discard() / job.promote()** | 完整的任务生命周期 |
| WP2.4 | 图片放大/高清 | Multi-Engine Pipeline | **Sharp + 远程API** | Sharp 替代 Pillow，性能10x提升 |
| WP2.4.1 | AI 放大（SeedVR2/ComfyUI） | Pipeline Fallback | **Bull Queue + axios** | 多级降级策略 |
| WP2.4.2 | 美图 AI 超清 | HMAC Signature | **Node.js crypto** | 替代Python hmac |
| WP2.4.3 | 本地 PIL 放大 | Sharp 图像处理 | **sharp.resize() + .sharpen()** | Sharp 性能远超 Pillow |
| WP2.5 | RunningHub 集成 | HTTP Client + Queue | **axios + Bull** | 任务提交与轮询 |
| WP2.5.1 | AI 应用提交/查询 | REST API Client | **axios + async/await** | 标准化HTTP调用 |
| WP2.5.2 | 工作流管理 | CRUD + Config | **TypeORM + JSON Schema** | 结构化存储 |
| WP2.5.3 | 素材上传 | Multipart Upload | **axios FormData** | 文件上传标准方案 |
| WP2.6 | 角度控制 | Async Task + Polling | **Bull Queue + WebSocket** | 异步任务+实时推送 |
| WP2.6.1 | ModelScope 角度生成 | Custom Provider | **Langchain Custom Wrapper** | 统一AI调用接口 |
| WP2.6.2 | 角度任务轮询 | WebSocket Push | **Socket.IO emit** | 实时状态推送 |
| WP2.7 | Provider 管理 | CRUD + Discovery | **TypeORM + axios** | 配置持久化+动态发现 |
| WP2.7.1 | Provider CRUD | REST API | **NestJS Controller + Service** | 标准CRUD模式 |
| WP2.7.2 | 连接测试/协议探测 | Health Check | **axios + timeout** | 连通性验证 |
| WP2.7.3 | 模型列表拉取 | API Discovery | **axios + cache** | 带缓存的模型发现 |
| WP2.7.4 | Gemini 图片能力探测 | Capability Probe | **axios + feature flag** | 能力探测与标记 |

---

### WP3 视频生成引擎

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP3.1 | 视频生成统一入口 | Provider 适配器 | **Langchain Custom Provider** | 统一AI调用接口 |
| WP3.2 | Veo 系列 | Google Provider | **Langchain Google Integration** | 官方支持 |
| WP3.3 | Sora-2 | OpenAI Provider | **Langchain OpenAI Integration** | 官方支持 |
| WP3.4 | 通义万相 | Custom Provider | **Langchain Custom Wrapper** | OpenAI兼容协议 |
| WP3.5 | 豆包 Seedance | Custom Provider | **Langchain Custom Wrapper** | OpenAI兼容协议 |
| WP3.6 | 即梦 | CLI Wrapper | **child_process.spawn()** | CLI调用封装 |
| WP3.7 | APIMart / OpenAI 协议适配 | Protocol Adapter | **Strategy Pattern** | 策略模式切换协议 |
| WP3.8 | 首帧/尾帧/参考图/参考视频 | Multi-Input Handler | **Multer + FFmpeg** | FFmpeg 处理视频帧 |
| WP3.9 | 云视频上传 | Cloud Upload Service | **axios + FormData** | 文件上传服务 |
| WP3.10 | LTX Director 时间线 | Frontend Timeline | **React + react-timeline-editor** | 前端时间线组件 |

---

### WP4 画布工作台

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP4.1 | 画布 CRUD 与项目管理 | REST API + DB | **NestJS + TypeORM** | 结构化存储 |
| WP4.1.1 | 画布创建/读取/保存/删除 | CRUD API | **NestJS Controller + Service** | 标准CRUD |
| WP4.1.2 | 画布回收站 | Soft Delete | **TypeORM @DeleteDateColumn** | 软删除机制 |
| WP4.1.3 | 画布元数据 | Lightweight Query | **TypeORM select partial** | 按需查询 |
| WP4.1.4 | 画布时间戳更新 | Touch API | **TypeORM update** | 更新时间戳 |
| WP4.2 | 节点系统 | React Flow | **@xyflow/react** | 成熟的节点图库 |
| WP4.2.1 | 图片卡片节点 | Custom Node | **React Flow Custom Node** | 可定制节点 |
| WP4.2.2 | 提示词节点 | Custom Node | **React Flow Custom Node** | 文本输入节点 |
| WP4.2.3 | API 生成节点 | Custom Node | **React Flow Custom Node** | 参数配置节点 |
| WP4.2.4 | Output 节点 | Custom Node | **React Flow Custom Node** | 结果展示节点 |
| WP4.2.5 | 循环节点 | Custom Node | **React Flow Custom Node** | 批量处理节点 |
| WP4.2.6 | LLM 节点 | Custom Node | **React Flow Custom Node** | LLM调用节点 |
| WP4.2.7 | 视频生成节点 | Custom Node | **React Flow Custom Node** | 视频参数节点 |
| WP4.2.8 | RunningHub 生成节点 | Custom Node | **React Flow Custom Node** | RH工作流节点 |
| WP4.2.9 | 批处理节点 | Custom Node | **React Flow Custom Node** | 批量处理节点 |
| WP4.3 | 画布交互 | React Flow Built-in | **@xyflow/react** | 内置平移/缩放/框选 |
| WP4.3.1 | 无限画布平移/缩放 | Viewport Control | **React Flow useViewport** | 内置视口管理 |
| WP4.3.2 | 节点拖放/框选/连线 | Drag & Drop | **React Flow DnD** | 内置拖拽系统 |
| WP4.3.3 | 小地图导航 | MiniMap | **React Flow MiniMap** | 内置小地图组件 |
| WP4.3.4 | 自动整理/对齐 | Layout Algorithm | **dagre / elkjs** | 自动布局算法 |
| WP4.3.5 | 图片拖放上传 | DnD + Upload | **react-dropzone** | 文件拖放组件 |
| WP4.4 | 图片编辑 | Fabric.js | **fabric.js** | 成熟的Canvas编辑库 |
| WP4.4.1 | 裁剪 | Fabric Crop | **fabric.js + react-cropper** | 裁剪工具 |
| WP4.4.2 | 扩展（Outpaint） | Fabric Outpaint | **fabric.js + AI API** | 扩展画布 |
| WP4.4.3 | 遮罩/画笔 | Fabric Brush | **fabric.js PencilBrush** | 画笔工具 |
| WP4.4.4 | 宫格切分 | Fabric Grid | **fabric.js + custom logic** | 网格切分 |
| WP4.5 | 画布资源管理 | File Service | **NestJS + fs/promises** | 文件管理服务 |
| WP4.5.1 | 资源检查 | Existence Check | **fs.access()** | 文件存在性检查 |
| WP4.5.2 | 打包下载（ZIP） | ZIP Generation | **archiver** | ZIP打包库 |
| WP4.5.3 | 本地保存 | File Save | **fs/promises** | 文件写入 |
| WP4.5.4 | 选择/打开保存文件夹 | Native Dialog | **electron.dialog** | Electron原生对话框 |
| WP4.5.5 | 项目导出/导入 | ZIP Import/Export | **archiver + extract-zip** | 项目打包导入导出 |
| WP4.5.6 | 项目本地保存 | Folder Save | **fs/promises** | 保存到指定目录 |
| WP4.6 | 多模式工作台 | Frontend State | **Zustand + React** | 状态管理切换模式 |
| WP4.6.1 | 简单模式 | Simplified UI | **React Components** | 简化界面组件 |
| WP4.6.2 | 专业模式 | Full Canvas | **React Flow** | 完整节点画布 |
| WP4.6.3 | 运营模式 | Design Preview | **React + Custom Layout** | 设计预览面板 |
| WP4.7 | 快捷提示词库 | CRUD API + DB | **NestJS + TypeORM** | 持久化存储 |
| WP4.7.1 | 提示词库 CRUD | REST API | **NestJS Controller** | 标准CRUD |
| WP4.7.2 | 提示词模板 | Template System | **JSON + Frontend** | 模板数据+前端渲染 |
| WP4.8 | 素材库 | CRUD API + DB | **NestJS + TypeORM** | 分类+条目管理 |
| WP4.8.1 | 分类管理 | Category CRUD | **NestJS Controller** | 分类CRUD |
| WP4.8.2 | 条目管理 | Item CRUD | **NestJS Controller** | 条目CRUD |
| WP4.9 | 智能画布 | Lightweight Canvas | **React + Custom Canvas** | 轻量画布实现 |
| WP4.9.1 | 多引擎选择 | Engine Selector | **React Select + Zustand** | 引擎选择器 |
| WP4.9.2 | 图片/视频双模式 | Mode Toggle | **React State** | 模式切换 |
| WP4.9.3 | 资产库集成 | Asset Panel | **React Components** | 资产面板组件 |
| WP4.9.4 | 全景预览 | 360 Viewer | **three.js + React** | 3D全景预览 |
| WP4.9.5 | 分组导出 | Group Export | **NestJS + archiver** | 分组打包导出 |
| WP4.10 | 一键详情页 | Wizard UI | **React Steps + AI API** | 向导式界面 |
| WP4.10.1 | 平台/尺寸/风格选择 | Config Form | **React Form** | 配置表单 |
| WP4.10.2 | AI 生成详情提示词 | LLM Chain | **Langchain Chain** | AI提示词生成 |
| WP4.11 | 历史记录 | Pagination API | **NestJS + TypeORM** | 分页查询 |
| WP4.11.1 | 生成历史 | History List | **TypeORM find + paginate** | 分页加载 |
| WP4.11.2 | 历史删除/批量操作 | Batch Delete | **TypeORM delete** | 批量删除 |

---

### WP5 AI 对话与工具

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP5.1 | GPT 对话聊天 | Chat Service | **Langchain + NestJS** | 统一AI对话接口 |
| WP5.1.1 | 文本聊天 | LLM Chain | **Langchain Conversation Chain** | 对话链管理 |
| WP5.1.2 | 流式聊天 | SSE Stream | **@nestjs/event-emitter + SSE** | 服务端推送 |
| WP5.1.3 | 图像生成模式 | Multi-Mode | **Langchain + Image Provider** | 多模态支持 |
| WP5.1.4 | 对话管理 | CRUD API | **NestJS + TypeORM** | 对话持久化 |
| WP5.1.5 | 参考图上传 | File Upload | **Multer + fs** | 文件上传 |
| WP5.2 | 画布 LLM 辅助 | Vision LLM | **Langchain Vision Model** | 多模态LLM |
| WP5.2.1 | 多模态 LLM 调用 | Vision API | **Langchain + GPT-4V/Gemini** | 视觉理解 |
| WP5.2.2 | 提示词辅助 | Prompt Helper | **Langchain Chain** | 提示词优化 |
| WP5.3 | 提示词反推 | Reverse Prompt | **Langchain + Vision** | 图片→提示词 |
| WP5.3.1 | 图片→提示词 | Image-to-Prompt | **Langchain Vision Chain** | 视觉反推 |
| WP5.4 | 参考图工具 | Web Scraper + Search | **axios + cheerio** | 网页抓取+搜索 |
| WP5.4.1 | 链接预览 | Link Preview | **axios + cheerio** | 网页图片提取 |
| WP5.4.2 | Bing 图片搜索 | Image Search | **axios + HTML parsing** | 图片搜索 |
| WP5.5 | 图像增强工具 | Multi-Engine | **Sharp + Remote API** | 本地+云端增强 |
| WP5.5.1 | 本地增强 | Local Processing | **sharp + custom pipeline** | 本地图像处理 |
| WP5.5.2 | 云端增强 | Cloud API | **axios + ModelScope** | 云端增强API |
| WP5.6 | FLUX Klein 合成终端 | Multi-Input UI | **React + Langchain** | 三图合成界面 |
| WP5.6.1 | 三图输入合成 | Multi-Image Input | **React Dropzone + Langchain** | 多图输入 |
| WP5.6.2 | LoRA 集成 | LoRA Config | **TypeORM + JSON** | LoRA配置管理 |

---

### WP6 CODEX 联动系统

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP6.1 | 会话管理 | Session Service | **NestJS + TypeORM** | 会话生命周期管理 |
| WP6.1.1 | Link 会话创建/更新 | Session CRUD | **TypeORM Entity** | 会话持久化 |
| WP6.1.2 | 会话完成/关闭 | Session Complete | **TypeORM update + cleanup** | 清理信标文件 |
| WP6.1.3 | 会话状态查询 | Session Query | **TypeORM find** | 实时状态查询 |
| WP6.1.4 | 活跃信标管理 | Beacon File | **fs/promises + JSON** | 单例检测文件 |
| WP6.2 | Bootstrap 引导 | Rule Installer | **fs/promises + crypto** | 规则安装与校验 |
| WP6.2.1 | 规则包安装/验证/修复 | Rule Sync | **fs + SHA256 (crypto)** | 文件同步与校验 |
| WP6.2.2 | SKILL 完整性检查 | Integrity Check | **crypto.createHash('sha256')** | SHA256校验 |
| WP6.2.3 | 版本门控 | Version Gate | **semver** | 版本比较 |
| WP6.3 | 需求收件箱 | Requirement Inbox | **NestJS + TypeORM** | 需求持久化 |
| WP6.3.1 | 需求行提交 | Batch Create | **TypeORM save** | 批量需求入库 |
| WP6.3.2 | 需求行查询 | Query API | **TypeORM find** | 需求列表查询 |
| WP6.3.3 | 参考图绑定 | Reference Binding | **TypeORM relation** | 关联参考图 |
| WP6.4 | 行级 Agent 跟踪矩阵 | Row Matrix | **NestJS + TypeORM** | 每行独立状态 |
| WP6.4.1 | Row Agent 状态管理 | State Management | **TypeORM Entity** | 状态持久化 |
| WP6.4.2 | 字段合并保护 | Merge Protection | **Custom Logic** | 防止覆盖关键字段 |
| WP6.5 | 命令队列 | Command Queue | **Bull Queue** | 命令异步处理 |
| WP6.5.1 | 命令提交 | Command Enqueue | **queue.add()** | 命令入队 |
| WP6.5.2 | 命令确认 | Command ACK | **job.update()** | 状态更新 |
| WP6.5.3 | 命令轮询 | Command Polling | **WebSocket + Bull** | 实时推送 |
| WP6.6 | Prompt Gate 与 QC | Validation Pipeline | **NestJS Pipes + Custom Validators** | 验证管道 |
| WP6.6.1 | 产品锁验证 | Product Lock Check | **Custom Validator** | 产品细节验证 |
| WP6.6.2 | 比例匹配验证 | Ratio Check | **Custom Validator** | 比例一致性 |
| WP6.6.3 | 显示文本泄漏检测 | Text Leak Check | **Regex + Custom Validator** | 中文/提示词泄漏 |
| WP6.6.4 | 角色引用分离 | Reference Separation | **Custom Validator** | 产品图vs参考图 |
| WP6.6.5 | 递归提示词检测 | Recursion Check | **Custom Validator** | 防止堆积 |
| WP6.7 | Codex 上下文 | Context Service | **NestJS Service** | 上下文生成 |
| WP6.7.1 | 上下文生成 | Context API | **JSON Generation** | 版本/配置/规则包 |
| WP6.7.2 | 编码健康检查 | Encoding Check | **iconv-lite** | 乱码检测修复 |

---

### WP7 客户端与发布

| 编号 | 活动 | 实现方案 | 技术选型 | 理由 |
|------|------|----------|----------|------|
| WP7.1 | 桌面客户端 | Electron Shell | **Electron + electron-builder** | 会议明确要求 |
| WP7.1.1 | 源代码模式启动器 | Dev Mode | **electron + vite** | 开发模式启动 |
| WP7.1.2 | 编译模式启动器 | Prod Mode | **electron-builder** | 生产模式打包 |
| WP7.1.3 | 网页端入口 | Web Mode | **Browser fallback** | 纯网页模式 |
| WP7.1.4 | 单实例检测 | Single Instance | **electron.app.requestSingleInstanceLock()** | 单实例锁 |
| WP7.1.5 | Windows 品牌化 | Branding | **electron.app.setAppUserModelId()** | 品牌化配置 |
| WP7.2 | 客户端认证 | Auth Service | **NestJS + keytar** | 跨平台密钥存储 |
| WP7.2.1 | API Key 验证 | Key Validation | **axios + gateway API** | 网关验证 |
| WP7.2.2 | 密钥加密存储 | Secure Storage | **keytar** | 跨平台替代DPAPI |
| WP7.2.3 | 解锁/换 Key/登出 | Auth Lifecycle | **NestJS Controller** | 认证生命周期 |
| WP7.2.4 | Gateway-Only 模式 | Gateway Mode | **Config Flag** | 发布包模式控制 |
| WP7.3 | API 账户管理 | Account Service | **NestJS + TypeORM** | 多账户管理 |
| WP7.3.1 | 多账户管理 | Account CRUD | **TypeORM Entity** | 账户持久化 |
| WP7.3.2 | 积分查看/刷新 | Usage Query | **axios + provider API** | 用量查询 |
| WP7.4 | 国际化（i18n） | i18n Framework | **react-i18next** | 成熟的i18n方案 |
| WP7.4.1 | 翻译框架 | i18n Setup | **i18next + react-i18next** | 国际化框架 |
| WP7.4.2 | 页面翻译文件 | Translation Files | **JSON + i18next** | 翻译文件管理 |
| WP7.5 | 构建与发布 | Build Pipeline | **electron-builder + GitHub Actions** | 自动化构建发布 |
| WP7.5.1 | 前端 JS 混淆 | Code Obfuscation | **javascript-obfuscator** | 代码保护 |
| WP7.5.2 | 发布暂存准备 | Release Prep | **Custom Script** | 发布准备脚本 |
| WP7.5.3 | Electron 打包 | Electron Build | **electron-builder** | 三端打包 |
| WP7.5.4 | 安装包生成 | Installer | **electron-builder NSIS/DMG/deb** | 安装程序生成 |
| WP7.5.5 | 发布验证 | Release Verify | **Custom Script + SHA256** | 完整性校验 |
| WP7.6 | 主题系统 | Theme Manager | **CSS Variables + Zustand** | 主题状态管理 |
| WP7.6.1 | 深色/浅色切换 | Theme Toggle | **CSS Variables** | CSS变量切换 |
| WP7.6.2 | iframe 同步 | Theme Sync | **postMessage** | 跨iframe同步 |
| WP7.7 | CODEX 规则包管理 | Rule Manager | **NestJS Service** | 规则包管理 |
| WP7.7.1 | 规则模板安装 | Rule Install | **fs/promises + crypto** | 规则安装 |
| WP7.7.2 | 规则包同步 | Rule Sync | **fs + SHA256** | 多目标同步 |
| WP7.7.3 | 预检工具 | Preflight Check | **Custom Script** | 完整性验证 |
| WP7.7.4 | 画布上下文生成 | Context Gen | **JSON Generation** | 上下文生成 |

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
| 焕创 AI 网关 | 统一 API 代理（GPT/Gemini/视频） | OpenAI 兼容 / APIMart |
| OpenAI GPT-Image-2 | 图片生成/编辑 | OpenAI Images API |
| Google Gemini | 图片生成 | Gemini API |
| ModelScope | 图片生成（通义万相/Z-Image/FLUX） | OpenAI 兼容 |
| RunningHub | ComfyUI 云端工作流、SeedVR2 放大 | RunningHub 专有 API |
| 即梦 (Jimeng) | 图片/视频生成 | CLI |
| 火山引擎 (ARK) | 视频生成（Seedance） | OpenAI 兼容 |
| OpenRouter | 多模型路由 | OpenAI 兼容 |
| KIE AI | 图片生成 | OpenAI 兼容 |
| 美图 (Meitu) | AI 超清放大 | 美图专有 API（HMAC） |
| ComfyUI (本地) | 本地图片生成 | ComfyUI HTTP API |
| GitHub | 自动更新 | GitHub API |
| Bing | 参考图搜索 | HTTP 抓取 |

---

## 六、当前架构痛点

| 问题 | 影响 |
|------|------|
| `main.py` 单文件 17,000 行 | 无法维护、无法协作开发 |
| `canvas.js` 单文件 24,000 行 | 前端逻辑耦合严重 |
| 无数据库，纯 JSON 文件 | 并发写入冲突、查询性能差、数据一致性无保障 |
| 原生 HTML + JS 无框架 | 组件复用困难、状态管理混乱 |
| iframe 多页面架构 | 页面间通信困难、重复加载、体验割裂 |
| pywebview 桌面壳 | 跨平台受限、调试困难 |
| 无前后端分离 | 无法独立部署、无法水平扩展 |
| Windows DPAPI 绑定 | 跨平台不可能 |

---

## 七、后端模块拆分建议

```
backend/
── src/
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
│   └── common/                 # 公共工具
├── test/
└── docker-compose.yml

frontend/
── src/
│   ├── App.tsx
│   ├── pages/                  # 页面组件
│   │   ├── Canvas/             # 画布工作台
│   │   ├── Chat/               # GPT 对话
│   │   ├── Settings/           # API 设置
│   │   ── ...
│   ├── components/             # 通用组件
│   │   ├── Canvas/             # 画布相关组件
│   │   ├── NodeEditor/         # 节点编辑器
│   │   ├── ImagePreview/       # 图片预览
│   │   └── ...
│   ├── stores/                 # Zustand 状态
│   ├── services/               # API 调用层
│   ├── hooks/                  # 自定义 Hooks
│   ├── i18n/                   # 国际化
│   └── types/                  # TypeScript 类型
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
| **Phase 1** | 后端 NestJS 框架搭建 + 数据库设计 + Provider 适配器模式 | P0 |
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
