---
layout: single
title: "学习记录：阿里云服务器 + 宝塔 + Docker 部署 New API 开源项目全流程"
date: 2026-07-28 00:00:00 +0800
categories: 部署
tags:
  - Docker
  - 宝塔面板
  - 阿里云
  - New API
  - Nginx
  - 开源
---

## 背景

最近接手了一个项目：在阿里云 ECS 上部署一个基于 [New API](https://github.com/QuantumNous/new-api) 的 AI 模型网关平台。甲方要求对页面进行定制化改造（更换品牌名、Logo、去掉官方文档链接等），并二次开源到 AtomGit。

在此之前我几乎没有 Docker 和服务器运维经验，整个过程踩了不少坑。本文记录整个部署和改造流程。

---

## 项目简介

New API 是一个基于 One API 的 LLM 网关与 AI 资产管理平台，支持多模型统一接入、用量统计、令牌管理等能力。后端使用 Go 语言，前端使用 React + Vite，整体通过 Docker 容器部署。

核心组件：
- **后端**: Go + Gin 框架
- **前端**: React + TypeScript + Vite + Tailwind CSS
- **数据库**: MySQL（存储用户、令牌、日志等）
- **缓存**: Redis（Session 和临时数据）
- **Web 服务器**: Nginx（反向代理 + SSL）

---

## 服务器环境

| 项目 | 详情 |
|------|------|
| 云服务商 | 阿里云 ECS |
| 操作系统 | Linux (CentOS / Alibaba Cloud Linux) |
| 管理面板 | 宝塔面板 |
| 容器运行时 | Docker 29.6.2 |
| Web 服务器 | Nginx (宝塔集成) |
| 数据库 | MySQL + Redis (本地安装) |

---

## 部署流程

### 第一步：拉取原始镜像

最初服务器上跑的是 `calciumion/new-api:latest` 官方镜像：

```bash
docker pull calciumion/new-api:latest

docker run -d --name new-api --restart always --network host \
  -e SQL_DSN="用户名:密码@tcp(127.0.0.1:3306)/new_api?charset=utf8mb4" \
  -e REDIS_CONN_STRING="redis://127.0.0.1:6379" \
  -e TZ=Asia/Shanghai \
  -v /www/wwwroot/new-api/data:/data \
  calciumion/new-api:latest
```

几个关键参数解释：
- `--network host`：容器共享宿主机网络，这样才能直接访问本地的 MySQL 和 Redis
- `-v` 挂载数据卷：持久化上传的文件和数据库
- `-e` 环境变量：传递数据库和 Redis 连接信息

### 第二步：克隆源码进行定制化修改

甲方要求去掉 New API 的官方文档和标语，换上自己的品牌名「焕创AI」。

先从 GitHub 克隆源码到本地：

```bash
git clone https://github.com/QuantumNous/new-api.git
```

主要修改点：
- `common/constants.go` → `SystemName = "焕创AI"`
- `web/src/lib/constants.ts` → `DEFAULT_SYSTEM_NAME = "焕创AI"`
- `web/src/lib/nav-modules.ts` → `docs: false` 隐藏文档入口
- `web/src/features/home/components/sections/hero.tsx` → 重写首页文案
- 全项目版权头从 `QuantumNous` 改为 `焕创AI`

### 第三步：构建自定义 Docker 镜像

在项目根目录执行：

```bash
docker build -t new-api-custom:latest .
```

构建完成后导出镜像文件：

```bash
docker save new-api-custom:latest | gzip > new-api-custom.tar.gz
```

### 第四步：上传镜像到服务器

这里遇到了第一个坑——SSH 直接登录服务器失败：

```
root@8.141.21.156: Permission denied (publickey)
```

因为本地没有配置 SSH 密钥，改用**宝塔面板的文件管理功能**直接上传 `new-api-custom.tar.gz` 到 `/tmp/` 目录。

然后在服务器上加载镜像：

```bash
gunzip -c /tmp/new-api-custom.tar.gz | docker load
```

### 第五步：替换容器

```bash
# 停止旧容器
docker stop new-api && docker rm new-api

# 用新镜像启动
docker run -d --name new-api --restart always --network host \
  -e SQL_DSN="用户名:密码@tcp(127.0.0.1:3306)/new_api?charset=utf8mb4" \
  -e REDIS_CONN_STRING="redis://127.0.0.1:6379" \
  -e TZ=Asia/Shanghai \
  -v /www/wwwroot/new-api/data:/data \
  new-api-custom:latest
```

---

## 踩坑记录

### 坑1：忘记 `--network host`，容器无法连接数据库

第一次启动新容器时没加 `--network host`，容器内的进程尝试连接 `127.0.0.1:3306`，但这个 IP 是容器自己的回环地址，不是宿主机的 MySQL。

```
[error] failed to initialize database, got error dial tcp 127.0.0.1:3306: connect: connection refused
```

**解决方法**：加上 `--network host`，让容器共享宿主机网络栈。

### 坑2：静态文件不被 Docker 容器内的应用响应

甲方提供了 SVG 格式的 Logo，放到项目的 `web/public/` 目录下重新构建镜像后，访问 `https://域名的/client-logo.svg` 返回的是 SPA 的 index.html 回退页面，而非 SVG 文件。

原因是 New API 后端将所有路由都交给了前端 SPA，而 Vite 构建时没有识别到这个新增的静态文件。

**解决方法**：在 Nginx 中单独配置该文件的路由，让 Nginx 直接返回而不经过 Docker 容器的代理：

```nginx
location = /client-logo.svg {
    root /www/wwwroot/ai.glowcreation.net;
    add_header Content-Type "image/svg+xml";
    expires 30d;
}
```

将其放入宝塔 Nginx 扩展目录后重载：

```bash
nginx -t && nginx -s reload
```

### 坑3：Docker 镜像名字不一致

本地构建时用的 `new-api-custom:latest`，启动命令写成了 `zhihong-studio/huanchuang:latest`，导致找不到镜像。

**解决方法**：用 `docker images` 确认实际镜像名，保持一致。

---

## 有用的排查命令

```bash
# 查看运行中的容器
docker ps -a

# 查看容器环境变量
docker inspect 容器名 --format '{{json .Config.Env}}' | python3 -m json.tool

# 查看容器挂载卷
docker inspect 容器名 --format '{{json .Mounts}}' | python3 -m json.tool

# 查看容器端口映射
docker port 容器名

# 查看容器日志
docker logs 容器名 --tail 20

# Nginx 配置测试
nginx -t && nginx -s reload

# 查看网站 Nginx 配置
cat /www/server/panel/vhost/nginx/域名.conf

# curl 测试响应头
curl -I https://域名/路径
```

---

## 宝塔面板 vs SSH 的使用场景

| 操作 | 推荐方式 | 原因 |
|------|----------|------|
| 上传大文件（镜像 tar.gz、Logo 图片） | 宝塔面板 | 快，拖拽上传，不需要配置 scp/rsync |
| 执行 Docker 命令 | SSH | 没有可交互的 Docker GUI |
| 修改 Nginx 配置 | SSH / 宝塔 | 两者都行，SSH 更灵活 |
| 管理 MySQL、Redis | 宝塔面板 | 有完善的图形化管理界面 |
| SSL 证书申请和管理 | 宝塔面板 | 一键 Let's Encrypt |

---

## 总结

整个部署流程总结为六个阶段：

1. **基础环境**: 阿里云 ECS + 宝塔面板 + Docker
2. **部署原始镜像**: 跑通官方 New API
3. **源码定制**: 修改品牌、文案、首页
4. **构建镜像**: 本地 build + save 导出
5. **部署更新**: 宝塔上传 + docker load + 重启容器
6. **持续维护**: Nginx 配置调整、静态文件托管

最大的收获是理解了 Docker 的网络模型（bridge vs host）、Nginx 反向代理的配置逻辑，以及宝塔面板和命令行如何配合使用。

---

*本文为个人学习记录，如有错误欢迎指正。*
