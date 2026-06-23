# 任务一 1.1：Multica 本地搭建记录

## 1. 环境与源码信息

- 源码仓库：`https://github.com/multica-ai/multica`
- 分析与部署源码路径：`C:/Users/陈俊辉/Documents/Codex/2026-05-24/new-chat/multica`
- 分析 commit：`45dae3185f01cdcd60967df82ca12c16917e566a`
- 实际运行环境：CentOS 7 虚拟机
- 虚拟机地址：`192.168.150.101`
- 运行方式：Docker Compose 自托管部署

技术栈识别：

- `server/`：Go 后端，Chi 路由，sqlc，pgx，gorilla/websocket
- `apps/web/`：Next.js 前端
- `apps/desktop/`：Electron 桌面端
- `packages/core`、`packages/ui`、`packages/views`：前端共享包
- 数据库：PostgreSQL 17 + `pgvector`

## 2. 本机环境限制与解决方式

当前 Windows 机器仅完成了源码分析，不具备完整自托管运行依赖：

```text
node --version -> v22.22.1
docker --version -> command not found
pnpm --version -> command not found
go version -> command not found
make --version -> command not found
```

因此改用 CentOS 7 虚拟机完成真实运行验证。虚拟机环境检查结果：

```text
CentOS Linux release 7.9.2009 (Core)
Docker version 20.10.8
docker-compose version 1.29.1
```

## 3. 实际搭建步骤

1. 将官方 `docker-compose.selfhost.yml` 作为基础部署文件。
2. 由于 CentOS 7 上使用的是 `docker-compose` v1，不支持新版 Compose 顶层 `name:` 字段，因此生成了一份兼容副本用于运行。
3. 由于虚拟机访问 Docker Hub 失败，`pgvector/pgvector:pg17` 改用可访问的镜像代理源：

```text
swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/pgvector/pgvector:pg17
```

4. 为了从 Windows 浏览器访问虚拟机中的前后端服务，端口映射设置为：

```text
Frontend -> 0.0.0.0:13000 -> 3000
Backend  -> 0.0.0.0:18081 -> 8080
```

5. 关键环境变量：

```text
FRONTEND_ORIGIN=http://192.168.150.101:13000
MULTICA_APP_URL=http://192.168.150.101:13000
CORS_ALLOWED_ORIGINS=http://192.168.150.101:13000
GOOGLE_REDIRECT_URI=http://192.168.150.101:13000/auth/callback
ALLOW_SIGNUP=true
```

6. 启动命令：

```bash
cd /opt/multica-selfhost
docker-compose -p multica -f docker-compose.v1.yml up -d
docker-compose -p multica -f docker-compose.v1.yml ps
```

## 4. 运行结果

容器启动成功：

```text
multica_backend_1    Up    0.0.0.0:18081->8080/tcp
multica_frontend_1   Up    0.0.0.0:13000->3000/tcp
multica_postgres_1   Up    5432/tcp (healthy)
```

服务验证结果：

```text
Windows 访问前端：http://192.168.150.101:13000 -> HTTP 200
Windows 访问后端：http://192.168.150.101:18081/health -> {"status":"ok"}
虚拟机本机访问前端 -> HTTP/1.1 200 OK
虚拟机本机访问后端 -> {"status":"ok"}
```

后端日志确认信息：

```text
connected to database
server starting port=8080
scheduler starting
```

数据库迁移已自动执行完成，后端服务已正常监听。

## 5. 遇到的问题与解决方案

### 问题 1：Windows 本机缺少完整运行依赖

解决方案：保留 Windows 侧源码分析，在 CentOS 7 虚拟机中完成 Docker 自托管运行验证。

### 问题 2：CentOS 7 的 `docker-compose` v1 不兼容官方 Compose 文件

解决方案：基于官方 `docker-compose.selfhost.yml` 生成一份兼容副本，去除顶层 `name:` 字段后启动。

### 问题 3：虚拟机无法直接访问 Docker Hub 拉取 `pgvector` 镜像

解决方案：改用华为云代理镜像源，成功拉取 PostgreSQL 17 + `pgvector` 运行镜像。

### 问题 4：默认只绑定 `127.0.0.1`，Windows 浏览器无法访问

解决方案：将前后端端口映射调整到 `0.0.0.0`，并同步配置 `FRONTEND_ORIGIN`、`MULTICA_APP_URL` 与 CORS。

## 6. 截图说明

建议在最终文档中放入以下 3 张真实截图：

1. 虚拟机终端执行 `docker-compose -p multica -f docker-compose.v1.yml ps` 的结果截图。
2. Windows 浏览器打开 `http://192.168.150.101:13000` 的 Multica 页面截图。
3. Windows 浏览器或接口工具访问 `http://192.168.150.101:18081/health` 返回 `{"status":"ok"}` 的截图。

以上截图均可基于当前已经运行成功的虚拟机环境直接获取。
