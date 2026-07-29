---
layout: single
title: "技术学习日记 — 四个核心技术栈深度入门"
published: true
date: 2026-08-01 12:00:00 +0800
categories: 学习笔记
tags: [NestJS, React Flow, Fabric.js, Langchain, Bull, Redis, Socket.IO, TypeScript]
---

# 技术学习日记 — 四个核心技术栈深度入门

> 这是一篇个人学习日记，记录了近期为了一个新项目而提前熟悉的四个核心技术栈。每个技术栈我都从"是什么、为什么重要、怎么用、高阶技巧"四个角度做了整理。

---

## 为什么是这四个？

最近要参与一个桌面端 AI 图像生成工作台的重构，技术栈跨度很大：从后端框架到前端画布引擎，从 AI 调度层到异步任务队列。我从中挑出了最核心的四个方向提前啃透：

1. **NestJS** — 后端从单文件巨石架构拆成模块化，NestJS 的 Module/DI 机制是根本方案
2. **React Flow + Fabric.js** — 前端核心交互是节点式画布 + 图片编辑
3. **Langchain JS** — 接入 10+ 个 AI Provider，需要统一调度层屏蔽差异
4. **Bull + Redis + Socket.IO** — 图片生成是耗时任务，必须有异步队列 + 实时推送

下面逐个记录学习心得。

---

## 一、NestJS — 后端模块化框架

### 为什么要学它

以前写后端，从 Express 到 FastAPI，功能一多就变成几千行的"上帝文件"，改一个功能要全局搜索，测试根本写不了。NestJS 用 **Module → Controller → Service** 三层强制拆分，从根本上杜绝了这个问题——不是"建议"你模块化，是框架结构让你**不得不**模块化。

### 核心概念速览

| 概念 | 作用 | 类比 |
|------|------|------|
| `@Module` | 把业务领域封装成独立模块 | 公司的"部门" |
| `@Controller` | 定义路由，接收 HTTP 请求 | 部门"前台" |
| `@Injectable` / Service | 写业务逻辑 | 部门"员工" |
| 依赖注入 (DI) | 框架自动创建对象并注入 | HR 自动分配人手 |
| `@UseGuards` | 鉴权拦截器 | 门禁系统 |
| Middleware | 请求/响应管道处理 | 快递分拣流水线 |
| Pipe | 数据验证和转换 | 安检仪 |
| Interceptor | 响应前后的统一处理 | 包装流水线 |

### 三层结构示例

```typescript
// 1. 模块定义
@Module({
  controllers: [ImageGenController],
  providers: [ImageGenService, ProviderRegistry, GptProvider, GeminiProvider],
  exports: [ImageGenService],
})
export class ImageGenModule {}

// 2. 路由层：接请求、回结果
@Controller('api/image-gen')
export class ImageGenController {
  constructor(private readonly service: ImageGenService) {}

  @Post('generate')
  @UseGuards(AuthGuard)
  async generate(@Body() dto: GenerateDto) {
    return this.service.generate(dto);
  }
}

// 3. 业务层：干活
@Injectable()
export class ImageGenService {
  constructor(private readonly registry: ProviderRegistry) {}

  async generate(dto: GenerateDto) {
    const provider = this.registry.get(dto.provider);
    return provider.generate(dto.prompt, dto.options);
  }
}
```

三层各管各的，每一层都可以独立 mock 测试。

### 高阶技巧：策略模式 + 依赖注入

有多个 AI Provider 时，传统写法是一堆 `if/else`。NestJS 用策略模式优雅解决：

```typescript
// 基类
export abstract class BaseImageProvider {
  abstract name: string;
  abstract generate(prompt: string, options: any): Promise<string[]>;
}

// 每个 Provider 独立实现
@Injectable()
export class GptProvider extends BaseImageProvider {
  name = 'gpt-image-2';
  async generate(prompt, options) { /* 调 OpenAI API */ }
}

@Injectable()
export class GeminiProvider extends BaseImageProvider {
  name = 'gemini';
  async generate(prompt, options) { /* 调 Gemini API */ }
}

// 注册表自动收集
@Injectable()
export class ProviderRegistry {
  constructor(
    private readonly gpt: GptProvider,
    private readonly gemini: GeminiProvider,
  ) {}

  private map = new Map<string, BaseImageProvider>();

  onModuleInit() {
    this.map.set(this.gpt.name, this.gpt);
    this.map.set(this.gemini.name, this.gemini);
  }

  get(name: string): BaseImageProvider {
    return this.map.get(name);
  }
}
```

新增 Provider：新建类实现基类，构造函数加一行，Module 的 `providers` 加一行——三处修改，不动任何业务代码。这就是**开闭原则**的落地。

### 补充：NestJS 生命周期

```
OnModuleInit → OnApplicationBootstrap → 处理请求 → OnModuleDestroy → BeforeApplicationShutdown → OnApplicationShutdown
```

- `OnModuleInit`：模块初始化后，适合做注册表收集
- `OnApplicationBootstrap`：所有模块就绪后，适合数据预热、定时任务启动
- 销毁钩子：优雅关闭（关数据库连接、清 Redis 队列）

---

## 二、React Flow + Fabric.js — 节点画布 + 图片编辑

### 为什么要学这两个

前端核心交互不是传统的表单+列表，而是一个**无限画布上的节点工作流**。用户拖入图片节点、提示词节点、生成节点，连线组成流水线，点击执行生成 AI 图片。生成后还需要裁剪、遮罩、扩展等编辑操作。

两个库分工：
- **React Flow**：节点、连线、拖拽、缩放、小地图——"画布骨架"
- **Fabric.js**：图片/文字/形状的对象模型、裁剪、画笔、滤镜——"内容编辑"

### React Flow 核心概念

```tsx
function PromptNode({ data }: NodeProps) {
  return (
    <div className="prompt-node">
      <Handle type="target" position={Position.Left} />
      <textarea value={data.prompt} onChange={...} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { image: ImageNode, prompt: PromptNode, generator: GeneratorNode };

<ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes}>
  <Background />
  <Controls />
  <MiniMap />
</ReactFlow>
```

关键心得：
- **Handle** 是节点输入/输出端口，`Position.Left` / `Position.Right` 控制位置
- 自定义节点就是普通 React 组件，可放任何内容
- `memo(Component)` 包裹节点防不必要重渲染，节点多时性能差距明显
- 建议直接用 **v12（@xyflow/react）** 新版 API

### Fabric.js 核心概念

把画布上的每个元素都当成可操作对象：

```typescript
const canvas = new fabric.Canvas(canvasEl, { width: 800, height: 600 });

// 加载图片
fabric.Image.fromURL(url, (img) => {
  img.scaleToWidth(400);
  img.set({ left: 100, top: 50 });
  canvas.add(img);
});

// 自由画笔（遮罩涂抹）
canvas.isDrawingMode = true;
canvas.freeDrawingBrush.color = 'black';
canvas.freeDrawingBrush.width = 20;

// 裁剪导出
const cropped = canvas.toDataURL({ left: x, top: y, width: w, height: h });

// 宫格切分
function splitGrid(rows: number, cols: number): string[] {
  const cw = canvas.width! / cols;
  const ch = canvas.height! / rows;
  const cells = [];
  for (let r = 0; r < rows; r++)
    for (let c = 0; c < cols; c++)
      cells.push(canvas.toDataURL({ left: c*cw, top: r*ch, width: cw, height: ch }));
  return cells;
}
```

### 两者配合

```
React Flow 画布（外层）
  ├── 图片节点（内嵌 Fabric.js Canvas）
  │     └── 双击放大 → Fabric.js 编辑模式
  ├── 提示词节点（普通表单）
  ├── 生成节点（按钮 + 进度条）
  └── 节点间连线
```

React Flow 管大画布上的节点布局和连线逻辑；Fabric.js 嵌入图片节点内部，管单张图片精细编辑。

### 补充：拖放到画布

```tsx
const [, dropRef] = useDrop({
  accept: 'NODE_TYPE',
  drop: (item, monitor) => {
    const position = screenToFlowPosition({
      x: monitor.getClientOffset().x,
      y: monitor.getClientOffset().y,
    });
    addNode({ id: crypto.randomUUID(), type: item.type, position, data: {} });
  },
});
```

---

## 三、Langchain JS — AI 统一调度层

### 为什么要学它

项目接了 GPT-4o、GPT-Image-2、Gemini、ModelScope 等 10 多个 AI Provider。统一层之前，每个 Provider 各写一套鉴权、调用、错误处理、重试逻辑。Langchain 的核心价值不是自带多少模型，而是提供了**统一接口 + 适配器模式**范式。

### 策略模式 + Base Class

```typescript
// 统一接口
interface ImageProvider {
  name: string;
  generate(prompt: string, options: GenerateOptions): Promise<GeneratedImage[]>;
  edit?(prompt: string, imageUrl: string): Promise<GeneratedImage[]>;
}

// 各 Provider 实现同一接口
class GptImageProvider implements ImageProvider {
  name = 'gpt-image-2';
  async generate(prompt, options) {
    const res = await this.client.images.generate({
      model: 'gpt-image-2', prompt,
      n: options.n ?? 1,
      size: `${options.width}x${options.height}`,
    });
    return res.data.map(img => ({ url: img.url!, provider: this.name }));
  }
}

class GeminiProvider implements ImageProvider {
  name = 'gemini';
  async generate(prompt, options) { /* 完全不同 SDK，同一接口 */ }
}

// 注册表
class ProviderRegistry {
  private providers = new Map<string, ImageProvider>();
  register(p: ImageProvider) { this.providers.set(p.name, p); }
  get(name: string) { return this.providers.get(name); }
}
```

### Langchain 的真实价值

Langchain JS 在上述架构中的角色不是替代 Provider 实现，而是提供：

1. **LLM 调用能力**：统一消息格式（`HumanMessage`、`SystemMessage`）
2. **多模态消息**：一条消息同时传文字+图片，自动处理 Base64 编码
3. **链式调用**：分析参考图 → 生成提示词 → 调用图片 API
4. **Prompt 模板**：可复用的提示词模板系统

```typescript
// 多模态链式调用
const analysis = await llm.invoke([
  new HumanMessage({
    content: [
      { type: 'text', text: '分析构图、光影、色调，输出图片生成提示词' },
      { type: 'image_url', image_url: { url: refImageUrl } },
    ],
  }),
]);
```

### 补充：Tool Calling（函数调用）

让 LLM 自主决定调用哪个外部工具：

```typescript
import { tool } from '@langchain/core/tools';
import { z } from 'zod';

const generateImageTool = tool(
  async ({ prompt, width, height }) => {
    return await imageProvider.generate(prompt, { width, height });
  },
  {
    name: 'generate_image',
    description: '根据描述生成电商产品图',
    schema: z.object({
      prompt: z.string().describe('图片描述提示词'),
      width: z.number().default(1024),
      height: z.number().default(1024),
    }),
  }
);

const llmWithTools = llm.bindTools([generateImageTool]);
```

对构建 Agent 类应用非常关键。

---

## 四、Bull + Redis + Socket.IO — 异步任务 + 实时推送

### 为什么要学它

AI 图片生成不是毫秒级操作——GPT-Image-2 通常 5-15 秒，某些模型 20-30 秒。同步接口会超时。正确做法：

```
用户点击生成 → API 立即返回 "已加入队列" → 后台慢慢生成
                                        → WebSocket 推送结果到前端
```

- **Bull**：任务队列，管理入队、执行、重试、优先级、进度
- **Redis**：Bull 的存储后端，任务数据持久化
- **Socket.IO**：双向实时通道，服务端主动推送

### Bull 任务队列

```typescript
@Injectable()
export class ImageGenQueue {
  constructor(@InjectQueue('image-gen') private queue: Queue) {}

  async add(dto: GenerateDto) {
    const job = await this.queue.add('generate', dto, {
      attempts: 3,
      backoff: { type: 'exponential', delay: 1000 },
      priority: dto.priority,
      removeOnComplete: 100,
    });
    return { jobId: job.id, status: 'queued' };
  }

  async getStatus(jobId: string) {
    const job = await this.queue.getJob(jobId);
    return {
      state: await job.getState(),
      progress: job.progress(),
      result: job.returnvalue,
    };
  }
}

@Processor('image-gen')
export class ImageGenProcessor {
  @Process('generate')
  async handle(job: Job<GenerateDto>) {
    await job.progress(10);
    const provider = this.registry.get(job.data.provider);
    const images = await provider.generate(job.data.prompt, job.data.options);
    await job.progress(90);
    return { images, completedAt: new Date() };
  }
}
```

### Socket.IO 实时推送

```typescript
@WebSocketGateway({ namespace: '/ws/tasks', cors: { origin: '*' } })
export class TaskGateway {
  @WebSocketServer() server: Server;

  emitProgress(canvasId: string, jobId: string, progress: number) {
    this.server.to(`canvas:${canvasId}`).emit('task:progress', { jobId, progress });
  }

  emitComplete(canvasId: string, result: any) {
    this.server.to(`canvas:${canvasId}`).emit('task:complete', result);
  }

  @SubscribeMessage('join')
  handleJoin(@ConnectedSocket() client: Socket, @MessageBody() canvasId: string) {
    client.join(`canvas:${canvasId}`);
  }
}
```

### 协作流程

```
前端 ──HTTP POST──→ NestJS Controller ──入队──→ Bull Queue
  │                                                    │
  │                  WebSocket                         │ 取出
  │               'task:complete'               Worker Processor
  └─────────────────────────────────────────── (调用 AI API)
```

### 补充：Bull 更多模式

- **延迟任务**：`queue.add('reminder', data, { delay: 600000 })` — 10分钟后执行
- **沙箱进程**：Worker 跑在独立进程，崩溃不影响主进程
- **重复任务**：`queue.add('cleanup', {}, { repeat: { cron: '0 3 * * *' } })` — 每天凌晨3点
- **并发控制**：`@Processor({ name: 'image-gen', concurrency: 5 })` — 最多同时5个

---

## 学习心得总结

| 技术栈 | 核心价值 | 最大收获 |
|--------|---------|---------|
| NestJS | 模块化 + 依赖注入 | 策略模式 + ProviderRegistry 是 DI 正确打开方式 |
| React Flow + Fabric.js | 节点画布 + 图片编辑 | 两库分工清晰，React 组件嵌套自然衔接 |
| Langchain JS | 统一 AI 接口 | 不是替代 Provider，是给多模态消息 + 链式调用 |
| Bull + Redis + Socket.IO | 异步任务 + 实时推送 | 三者配合才能不阻塞、有反馈 |

技术选型没有银弹，每个选择都有场景和边界。关键是想清楚**当前问题是什么，这个技术解决的是哪一类问题**。

---

*写于 2026 年 8 月，持续学习中。*
