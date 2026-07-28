---
layout: single
title: "从零部署New API：阿里云+宝塔面板+Docker完整指南"
date: 2026-07-28 00:00:00 +0800
categories: 
  - 部署
tags:
  - Docker
  - 宝塔面板
  - New API
  - 阿里云
  - Nginx
  - SSL
  - MySQL
  - Redis
toc: true
toc_sticky: true
---

## 一、项目背景

### 1.1 什么是New API

New API（原名 One API）是一个开源的 **AI 模型网关与资产管理平台**，核心功能包括：

- **多模型统一接入**：将 OpenAI / Gemini / DeepSeek 等不同厂商的 API 统一为一个兼容 OpenAI 格式的入口
- **多租户管理**：支持创建多个用户，分别设定额度、有效期，实现按量计费
- **渠道负载均衡**：可添加多个同类型渠道（多个 API Key），按优先级或权重自动分发请求
- **用量统计**：记录每次调用消耗的 Token 数量和费用

架构示意：

```
客户端 → New API（令牌验证 + 额度扣减）→ 渠道（真实的API Key）→ 各AI服务商
```

### 1.2 为什么需要自行部署

我们的业务场景是AI图像生成平台，需要调用多个AI厂商的API，同时要提供给多个客户使用。自行部署 New API 可以实现：

- 隐藏真实 API Key，只暴露虚拟令牌给客户端
- 对每个客户分别设置使用额度
- 统计每个客户的用量，便于计费
- 作为API调用的统一入口，方便后期扩展和切换供应商

### 1.3 部署环境总览

| 项目       | 详情                            |
| ---------- | ------------------------------- |
| 云服务商   | 阿里云 ECS                      |
| 操作系统   | Linux (Alibaba Cloud Linux 3)   |
| 管理面板   | 宝塔面板 6.0                    |
| 容器运行时 | Docker 29.6.2                   |
| Web 服务器 | Nginx 1.24（宝塔集成）          |
| 数据库     | MySQL 8.0（宝塔原生安装）       |
| 缓存       | Redis 7.2（宝塔原生安装）       |

---

## 二、服务器环境准备

### 2.1 购买 ECS 并获取登录信息

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com)
2. 购买 ECS 实例，推荐配置：2核2G起步，系统盘40GB ESSD，操作系统选 **Alibaba Cloud Linux 3**（基于 CentOS）
3. 购买成功后，在实例列表中可以看到 **公网IP** 和 **内网IP**
4. 如果忘记 root 密码，在实例详情页 → "重置密码" 修改后重启服务器生效

### 2.2 连接服务器

#### 方式一：阿里云 CloudShell（推荐新手）

在 ECS 实例列表中，点击右侧的 **"远程连接"** → 选择 **"通过Workbench远程连接"**：

- 用户名：`root`
- 密码：输入你设置的密码

连接成功后会显示类似：`root@iZxxxxxxxxxxxxx:~#`

#### 方式二：本地终端SSH

```bash
ssh root@你的服务器IP
```

### 2.3 安全组放行端口

部署前需要在阿里云安全组中放行以下端口：

1. 进入 ECS 控制台 → 实例 → 点击实例ID → **安全组**
2. 点击 **安全组ID** → **入方向** → **手动添加**

| 协议   | 端口   | 授权对象      | 说明          |
| ------ | ------ | ------------- | ------------- |
| TCP    | 22     | 0.0.0.0/0    | SSH 远程登录  |
| TCP    | 80     | 0.0.0.0/0    | HTTP 访问     |
| TCP    | 443    | 0.0.0.0/0    | HTTPS 访问    |
| TCP    | 8888   | 0.0.0.0/0    | 宝塔面板      |
| TCP    | 3000   | 0.0.0.0/0    | New API 直接访问（调试用，后期关闭） |

> **注意**：端口根据实际需要逐步放行，不要一次性全部打开。尤其是MySQL(3306)和Redis(6379)只需要本机访问，**不需要对外放行**。

---

## 三、宝塔面板安装与配置

### 3.1 安装宝塔面板

SSH 登录服务器后，执行以下安装命令：

```bash
wget -O install.sh https://download.bt.cn/install/install_6.0.sh && bash install.sh ed8484bec
```

安装过程中会提示：

```
Do you want to install Bt-Panel to the /www directory now?(y/n):
```

输入 `y` 回车，等待安装完成（约5-15分钟）。

### 3.2 获取面板登录信息

安装完成后，终端会显示如下信息（**必须妥善保存**）：

```
========================面板账户登录信息==========================
 外网面板地址: https://你的服务器IP:8888/xxxxxxxx
 内网面板地址: https://你的内网IP:8888/xxxxxxxx
 username: 你的用户名
 password: 你的密码
==================================================================
```

- **外网面板地址**：从外网访问宝塔的URL，最后的 `/xxxxxxxx` 是安全入口
- **username / password**：宝塔登录凭据

### 3.3 登录宝塔面板

1. 浏览器打开外网面板地址（如 `https://你的服务器IP:8888/xxxxxxxx`）
2. 首次访问会提示安全警告，点击"高级 → 继续访问"即可（宝塔使用自签名证书）
3. 输入username和password登录
4. 首次登录可能要求绑定宝塔账号，按提示操作或跳过

### 3.4 安装运行环境

登录后宝塔会弹出 **"推荐安装套件"**，**直接关掉**，我们进入软件商店手动选择安装：

**左侧菜单 → 软件商店**，依次搜索并安装以下组件：

| 组件         | 安装方式     | 版本建议     | 用途             |
| ------------ | ------------ | ------------ | ---------------- |
| **Nginx**    | 软件商店安装 | 1.24 或 1.26 | 反向代理 + SSL   |
| **MySQL**    | 软件商店安装 | 5.7 或 8.0   | 存储用户/日志等  |
| **Redis**    | 软件商店安装 | 7.0 或 7.2   | 缓存和会话管理   |
| **Docker管理器** | 软件商店安装 | 最新版       | 运行 New API 容器 |

> **安装顺序建议**：Nginx → MySQL → Redis → Docker管理器，一个一个装，等每个完成再装下一个。安装完成后状态显示"运行中"即正常。

### 3.5 验证安装

在服务器终端验证各组件：

```bash
# 检查 Nginx
nginx -v

# 检查 MySQL
mysql --version

# 检查 Redis
redis-cli --version

# 检查 Docker
docker --version
```

### 3.6 如忘记宝塔密码

SSH登录服务器后执行：

```bash
bt default
```

会重新显示面板地址和登录信息。如果需修改密码：

```bash
bt
```

在弹出的菜单中选择 `5` 修改密码。

---

## 四、数据库与Redis配置

### 4.1 创建 MySQL 数据库（给 New API 用）

1. 宝塔面板 → **左侧菜单 → 数据库**
2. 点击 **"添加数据库"**
3. 填写信息：

| 字段     | 填写内容                       | 备注           |
| -------- | ------------------------------ | -------------- |
| 数据库名 | `new_api`                      | New API专用    |
| 用户名   | `new_api`                      | 数据库用户     |
| 密码     | 点击"随机生成"或自定义         | **务必记下来** |
| 权限     | 默认（localhost）              | 仅本机访问     |

4. 点击"提交"

**重要：记录以下数据库连接信息，后续部署要使用**

```
数据库名: new_api
用户名:   new_api
密码:     你的数据库密码（示例中为随机生成的密码，请用你的实际密码）
地址:     127.0.0.1
端口:     3306
```

### 4.2 确认 Redis 状态

1. 宝塔面板 → **软件商店 → 已安装**
2. 找到 **Redis**，确认状态为"运行中"
3. 点击"设置"，查看配置文件中 `port` 一行，默认为 `6379`
4. Redis 连接信息：`redis://127.0.0.1:6379`

> 宝塔安装的 MySQL 和 Redis 默认没有设置密码（仅限本地 `127.0.0.1` 访问）。如果要远程访问，需要在宝塔中设置密码并放行端口。**生产环境强烈建议设置密码并限制访问来源！**

---

## 五、部署 New API

### 5.1 创建项目目录

SSH登录服务器，创建持久化数据目录：

```bash
mkdir -p /www/wwwroot/new-api/data
```

### 5.2 拉取并启动容器

New API 的 Docker 镜像名为 `calciumion/new-api:latest`。使用 `--network host` 模式让容器共享宿主机网络（这样容器可以直接访问本机的 MySQL 和 Redis）：

```bash
docker run -d \
  --name new-api \
  --restart always \
  --network host \
  -e TZ=Asia/Shanghai \
  -e SQL_DSN="new_api:你的数据库密码@tcp(127.0.0.1:3306)/new_api?charset=utf8mb4" \
  -e REDIS_CONN_STRING="redis://127.0.0.1:6379" \
  -v /www/wwwroot/new-api/data:/data \
  calciumion/new-api:latest
```

**参数说明**：

| 参数              | 说明                                         |
| ----------------- | -------------------------------------------- |
| `-d`              | 后台运行容器                                 |
| `--name new-api`  | 容器命名为 `new-api`                         |
| `--restart always` | 容器异常退出或宿主机重启后自动重启           |
| `--network host`  | 共享宿主机网络栈，**必须加**，否则连不上本机MySQL |
| `-e TZ`           | 时区设为上海                                 |
| `-e SQL_DSN`      | MySQL连接字符串                              |
| `-e REDIS_CONN_STRING` | Redis连接地址                            |
| `-v`              | 挂载目录，持久化数据和日志                   |

> **替换提醒**：请把命令中的 `你的数据库密码` 替换为第4.1步记录的密码。连接字符串格式：`用户名:密码@tcp(127.0.0.1:3306)/数据库名?charset=utf8mb4`

### 5.3 验证容器状态

```bash
# 查看容器是否在运行
docker ps

# 应该看到类似输出：
# CONTAINER ID   IMAGE                       COMMAND      STATUS         PORTS     NAMES
# 容器ID         calciumion/new-api:latest   "/new-api"   Up 10 seconds             new-api

# 查看容器日志
docker logs new-api --tail 20
```

正常日志应包含：

```
[SYS] using MySQL as database
[SYS] database migration started
[SYS] Redis is enabled
New API v1.0.0-rc.21 ready in 1038 ms
➜  Network: http://10.0.0.x:3000/
```

如果日志出现 `connection refused` 错误，**跳到本文第7节常见问题**。

### 5.4 放行3000端口

New API 默认监听3000端口，需要在阿里云安全组和系统防火墙中放行。

**第一步：阿里云安全组**

入方向添加 TCP/3000 允许 0.0.0.0/0

**第二步：系统防火墙**

```bash
ufw allow 3000/tcp
```

### 5.5 首次访问与初始化

浏览器打开 `http://你的服务器IP:3000`，首次会看到初始化页面：

1. **设置管理员账号**：填写用户名、密码
2. **选择使用模式**：
   - 自用模式：适合个人使用
   - **对外运营模式**：适合给多个客户使用，支持多用户管理、额度充值（推荐选这个）
3. 点击"完成初始化"
4. 用设置的账号密码登录管理后台

> 截图位置：初始化页面截图

---

## 六、域名绑定与 SSL 证书

### 6.1 域名 DNS 解析

1. 登录阿里云 → 域名 → 域名列表 → 找到你的域名
2. 点击 **"解析"** → **"添加记录"**

| 字段         | 填写内容                                |
| ------------ | --------------------------------------- |
| 记录类型     | A                                       |
| 主机记录     | `ai`（如果用 `ai.yourdomain.com` 格式） |
| 记录值       | 你的服务器公网IP，如 `XXX.XXX.XXX.XXX`     |
| TTL          | 10分钟                                  |

3. 保存后等待1-2分钟，用 `ping ai.yourdomain.com` 验证解析是否生效

### 6.2 在宝塔中添加站点

1. 宝塔面板 → **网站** → **添加站点**
2. 填写域名 `ai.yourdomain.com`，PHP版本选 **纯静态**，不创建数据库

### 6.3 申请免费SSL证书（Let's Encrypt）

1. 点击站点右侧 **"设置"** → 左侧 **"SSL"**
2. 选择 **"Let's Encrypt"** 标签
3. 验证方式：
   - **文件验证**：Let's Encrypt通过80端口访问验证文件（国内服务器可能超时）
   - **DNS验证**（推荐）：勾选"手动解析"，会生成一条TXT记录，去阿里云DNS添加后再回来验证

> 截图位置：SSL申请界面

4. 证书申请成功后，打开 **"强制HTTPS"** 开关
5. 宝塔会自动在证书到期前续期（Let's Encrypt证书有效期为90天）

### 6.4 配置 Nginx 反向代理

将域名流量转发到 New API 的3000端口：

1. 站点设置 → 左侧 **"反向代理"** → **"添加反向代理"**

| 字段       | 填写内容                |
| ---------- | ----------------------- |
| 代理名称   | `new-api`               |
| 目标 URL   | `http://127.0.0.1:3000` |
| 发送域名   | `$host`                 |

2. 保存后，点击反向代理规则右侧的 **"配置文件"**，编辑配置：

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SSE流式传输关键配置（必须添加）
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    # 上传文件大小限制
    client_max_body_size 50m;
}
```

**关于 `proxy_buffering off`**：New API 使用 SSE（Server-Sent Events）实现模型调用的流式输出。如果不关闭 Nginx 缓冲，流式响应会被缓存直到完成才返回给客户端，导致前端看不到打字机效果。

3. 保存后，在服务器终端重载Nginx：

```bash
nginx -t && nginx -s reload
```

### 6.5 验证 HTTPS 访问

浏览器打开 `https://ai.yourdomain.com`，应看到 New API 登录页面，地址栏显示锁头图标。

### 6.6 禁用 IP 直接访问（生产环境安全加固）

部署完成后，为安全起见，应禁止通过 IP 直接访问 New API，只允许通过域名访问。

**第一步：关闭3000端口的外部访问**

1. 从阿里云安全组中删除 TCP/3000 的入方向规则

**第二步：配置 Nginx 拦截 IP 访问**

在宝塔中给默认站点添加配置，拦截所有未匹配域名的请求。编辑 `/www/server/panel/vhost/nginx/0.default.conf`：

```nginx
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    server_name _;
    ssl_certificate /www/server/panel/vhost/cert/yourdomain.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/yourdomain.com/privkey.pem;
    return 444;  # 直接关闭连接，不返回任何内容
}
```

执行 `nginx -t && nginx -s reload` 重载配置。

> 这样配置后，通过 `http://你的服务器IP:3000` 或 `https://你的服务器IP` 都无法直接访问，必须通过已绑定的域名访问。

---

## 七、常见问题与解决方案

### 7.1 容器启动后反复重启，日志提示 `connection refused`

```
[error] failed to initialize database, got error dial tcp 127.0.0.1:3306: connect: connection refused
```

**原因**：未使用 `--network host`，容器内的 `127.0.0.1` 指向容器自身而非宿主机，无法连接宿主机的 MySQL。

**解决**：

```bash
# 停止并删除旧容器
docker stop new-api && docker rm new-api

# 重新启动时加上 --network host
docker run -d --name new-api --restart always --network host ...（其余参数不变）
```

### 7.2 镜像拉取失败

如果 `calciumion/new-api:latest` 拉取失败，可以尝试其他镜像源或手动指定版本号。

国内服务器可配置 Docker 镜像加速器（在 `/etc/docker/daemon.json` 中添加阿里云镜像加速地址）。

### 7.3 SSL 证书申请失败

**文件验证超时**（Timeout during connect）：

Let's Encrypt 验证服务器在海外，访问国内服务器可能超时。改用 **DNS 验证** 方式（见第6.3节）。

**403 错误**：

检查 DNS 解析是否生效：`ping 你的域名`。确认返回的 IP 是服务器 IP。

### 7.4 Nginx提示 `nginx.service is not active`

宝塔安装的 Nginx 不使用 systemd 管理。正确操作方式：

```bash
# 不要在宝塔服务器上使用 systemctl restart nginx
# 正确方式：
nginx -s reload    # 重载配置
nginx -t           # 测试配置
```

### 7.5 MySQL 和 Redis 数据备份

宝塔面板自带定时备份功能：**计划任务** → 添加任务，选择备份数据库和网站目录。建议每天备份一次，保留最近7天的备份文件。

---

## 八、附录：常用操作命令速查

### Docker 相关

```bash
# 查看所有容器（含已停止的）
docker ps -a

# 查看容器日志（最近20行）
docker logs new-api --tail 20

# 实时查看容器日志
docker logs -f new-api

# 进入容器内部
docker exec -it new-api /bin/sh

# 停止容器
docker stop new-api

# 删除容器
docker rm new-api

# 查看容器环境变量
docker inspect new-api --format '{{json .Config.Env}}' | python3 -m json.tool
```

### 网络排查

```bash
# 查看端口监听状态
ss -tlnp | grep 3000
ss -tlnp | grep 80
ss -tlnp | grep 443

# 查看防火墙状态
ufw status

# 本地测试HTTP响应
curl -I http://127.0.0.1:3000

# 测试HTTPS（忽略证书验证）
curl -I https://127.0.0.1 --insecure
```

### Nginx 相关

```bash
# 查看站点配置文件
cat /www/server/panel/vhost/nginx/yourdomain.com.conf

# 查看错误日志
tail -50 /www/wwwlogs/yourdomain.com.error.log

# 测试配置并重载
nginx -t && nginx -s reload
```

---

## 九、总结

本文详细记录了在阿里云ECS服务器上，通过宝塔面板和Docker部署 New API 的完整流程。整个过程分为以下几个阶段：

| 阶段                 | 关键操作                                         |
| -------------------- | ------------------------------------------------ |
| 1. 环境准备           | 购买ECS、安全组放行端口、SSH连接                 |
| 2. 宝塔安装           | 一键安装脚本、登录面板                           |
| 3. 组件安装           | Nginx、MySQL、Redis、Docker                      |
| 4. 数据库配置         | 创建new_api数据库、确认Redis运行                 |
| 5. New API部署        | Docker拉取镜像、启动容器、初始化管理后台         |
| 6. 域名与SSL          | DNS解析、宝塔添加站点、Let's Encrypt证书、反向代理 |
| 7. 安全加固           | 关闭IP直接访问、禁用不必要的端口                 |

部署完成后，New API 作为 AI 调用的统一网关，配合后续部署的业务系统（如AI图像生成平台），即可实现对多AI服务商的统一接入和对多客户的分权分域管理。

---

*本文为个人部署学习记录，环境为阿里云ECS + Alibaba Cloud Linux 3，其他服务器环境（如Ubuntu/CentOS）的宝塔安装命令可能不同，请参考[宝塔官方文档](https://www.bt.cn)。*
