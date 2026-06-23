# 任务一 1.1：Multica 本地搭建记录

## 1. 环境与源码信息

- 源码仓库：`https://github.com/multica-ai/multica`
- 本地路径：`C:/Users/陈俊辉/Documents/Codex/2026-05-24/new-chat/multica`
- 分析 commit：`45dae3185f01cdcd60967df82ca12c16917e566a`
- 技术栈识别：
  - `server/`：Go 后端，Chi 路由，sqlc，pgx，gorilla/websocket
  - `apps/web/`：Next.js 前端
  - `apps/desktop/`：Electron 桌面端
  - `packages/core`、`packages/ui`、`packages/views`：前端共享包
  - `PostgreSQL + Redis`：本地自托管依赖

## 2. 搭建步骤

```bash
git clone https://github.com/multica-ai/multica.git
cd multica
```

阅读项目说明：

```bash
type AGENTS.md
type CLAUDE.md
type README.md
type SELF_HOSTING.md
```

项目根目录给出的常用命令：

```bash
make dev
make start
make server
make daemon
make test
pnpm install
pnpm dev:web
```

## 3. 实际执行情况

本次笔试环境已成功完成源码克隆和静态代码分析，并确认本机缺少完整启动 Multica 所需的基础依赖。环境检查结果如下：

```text
node --version -> v22.22.1
docker --version -> command not found
pnpm --version -> command not found
go version -> command not found
make --version -> command not found
```

因此当前机器无法真实执行 `make dev` 或启动 PostgreSQL/Redis/Docker 依赖。若在完整开发环境中运行，建议按以下顺序补充截图：

1. Docker Desktop 启动 PostgreSQL 和 Redis。
2. `pnpm install` 安装前端依赖。
3. `make dev` 启动后端、前端和 daemon。
4. 打开浏览器访问本地 Web 页面，截取运行成功页面。
5. 截取 daemon 日志中 runtime online / heartbeat / task claim 等信息。

## 4. 遇到的问题与解决方案

### 问题 1：项目规模大，直接全量阅读效率低

解决方案：先阅读 `AGENTS.md` 和 `CLAUDE.md`，确定后端、daemon、WebSocket 和任务队列所在目录，再使用关键词追踪：

- `ClaimAgentTask`
- `StartAgentTask`
- `CompleteAgentTask`
- `FailAgentTask`
- `runtime_sweeper`
- `heartbeat`
- `FOR UPDATE SKIP LOCKED`

### 问题 2：本地运行依赖较重

Multica 是 Turborepo monorepo，并依赖 PostgreSQL、Redis、Go、Node、pnpm。笔试分析阶段可以先完成源码级证据链，真正运行截图需要在完整环境补充。

### 问题 3：任务状态分散在 Handler、Service、SQL、Daemon 中

解决方案：按请求链路追踪，而不是按文件阅读：

```text
daemon client -> HTTP route -> handler -> TaskService -> sqlc query -> database
```

例如任务领取链路：

```text
server/internal/daemon/client.go
  -> POST /api/daemon/runtimes/{runtimeId}/tasks/claim
server/cmd/server/router.go:505
  -> h.ClaimTaskByRuntime
server/internal/handler/daemon.go:1159
  -> TaskService.ClaimTaskForRuntime
server/internal/service/task.go:1009
  -> ClaimAgentTask SQL
server/pkg/db/queries/agent.sql:266
```

## 5. 截图说明

本次交付保留环境检查日志作为可复现说明。完整运行成功截图需要在安装 Docker、Go、pnpm、make 后执行 `make dev` 获取。
