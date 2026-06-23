# 任务四：AI 工作流记录

## 4.1 AI 编程工具配置

### 配置 1：项目级 AGENTS.md

文件：`task4/ai-configs/AGENTS.md`

解决的问题：避免 AI 在不了解项目结构时直接生成代码，要求它先分析技术栈、项目规则、数据流和影响范围。

生效场景：处理大型仓库、多人协作项目、笔试项目或需要保留证据链的源码分析任务。

迭代优化：从“让 AI 写答案”改为“让 AI 先读规则文件，再输出代码路径和行号”，减少空泛分析。

### 配置 2：Codex 工作流说明

文件：`task4/ai-configs/codex-workflow.md`

解决的问题：规范使用 AI 完成工程任务的顺序，包括阅读、搜索、实现、测试、打包。

生效场景：本次笔试题中，AI 先读取题目 Markdown，再克隆 Multica 仓库，之后追踪后端 Handler、Service、SQL 和 daemon 代码。

迭代优化：特别增加“不伪造外部结果”的约束。比如任务三需要真实 PR，但当前没有 GitHub 登录态，因此只提交可执行修复方案和 PR 占位说明。

## 4.2 关键场景实录

### 场景 1：Multica 任务领取链路追踪

卡在哪里：Multica 仓库较大，任务状态分散在 daemon、handler、service、sqlc query 和 sweeper 中，直接阅读会迷失。

提示词：

```text
请仔细阅读笔试题，克隆 Multica 源码，围绕 Agent 崩溃和并发任务领取两个场景，追踪入口函数、Service、SQL 查询和状态变迁，要求给出文件路径和行号。
```

AI 输出的价值：

- 先识别仓库结构：`server/`、`apps/web/`、`apps/desktop/`、`packages/`。
- 找到关键路径：
  - `server/cmd/server/router.go:505`
  - `server/internal/handler/daemon.go:1159`
  - `server/internal/service/task.go:1009`
  - `server/pkg/db/queries/agent.sql:266`
- 发现 `FOR UPDATE SKIP LOCKED` 是并发领取的核心机制。
- 发现 `runtime_sweeper.go` 和 `RecoverOrphanedTasksForRuntime` 是防任务泄漏的关键机制。

我的修正：

AI 初步容易把“Agent 离线”直接理解为 WebSocket 断开。我进一步要求它区分 daemon heartbeat、runtime offline、task running timeout 和重启恢复，最后形成了更准确的状态机分析。

### 场景 2：任务编排引擎实现

卡在哪里：题目要求同时覆盖 DAG、依赖调度、状态机、失败策略、并发限制和测试。如果直接写成应用，会时间过长。

提示词：

```text
请实现一个最小但完整的多 Agent 任务编排引擎，可以用 Python，必须包含 DAG 构建、环检测、任务调度、状态机、并发限制，以及题目列出的测试用例。
```

AI 输出的价值：

- 将实现收敛为内存核心引擎，不引入 Web 框架和数据库。
- 使用 `dependencies` 和 `dependents` 两个邻接表存储 DAG。
- 使用 Kahn 拓扑排序检测循环依赖。
- 用 `claim_task()` 模拟 Agent 并发领取。
- 用 `unittest` 覆盖 8 个测试用例。

我的修正：

AI 一开始容易把 `skip` 策略理解为“跳过后所有后继都继续执行”。我将其修正为：依赖失败任务的后继应取消，不依赖它的分支继续执行。这样更符合 DAG 的依赖语义。

## 4.3 本次 AI 使用边界

AI 用于：

- 阅读题目和源码。
- 追踪代码路径。
- 生成设计文档草稿。
- 实现核心引擎和测试。
- 整理交付目录。

人工判断用于：

- 不伪造运行截图。
- 不伪造 GitHub PR。
- 选择最小可运行实现而不是过度搭建完整应用。
- 校正故障场景结论和失败策略语义。

