# 任务三：开源贡献修复分析报告

## 1. 选择的问题

本报告选择任务一中发现的改进点作为潜在开源贡献方向：

> 当前 Multica 已经通过 runtime heartbeat、runtime sweeper、`FailStaleTasks`、`RecoverOrphanedTasksForRuntime` 等机制防止任务永久卡在 `running`。但 `runningTimeoutSeconds` 是服务端全局常量，任务级差异较大时不够精细：短任务失败发现偏慢，长任务又可能误判风险较高。

相关代码：

- `server/cmd/server/runtime_sweeper.go:35-45`
- `server/cmd/server/runtime_sweeper.go:241-261`
- `server/pkg/db/queries/agent.sql:462-476`

## 2. 根因分析

现有 `FailStaleTasks` 主要依赖：

```text
status = 'running'
AND started_at < now() - runningTimeoutSeconds
```

这是一种粗粒度租约。它适合作为兜底机制，但无法表达不同任务的预期运行时长。例如：

- 轻量代码检查任务可能 5 分钟内完成，9000 秒后才发现异常过慢。
- 大型重构任务可能超过 9000 秒，存在被误判为 timeout 的风险。

## 3. 修复方案

### 方案 A：任务级 timeout 字段

新增 `agent_task_queue.timeout_seconds`，创建任务时可写入预期超时时间。`FailStaleTasks` 优先使用任务自身 timeout，未配置时回退到全局 `runningTimeoutSeconds`。

关键 SQL 思路：

```diff
UPDATE agent_task_queue
SET status = 'failed',
    completed_at = now(),
    error = 'task timed out',
    failure_reason = 'timeout'
WHERE (status = 'dispatched'
       AND dispatched_at < now() - make_interval(secs => @dispatch_timeout_secs::double precision))
   OR (status = 'running'
-      AND started_at < now() - make_interval(secs => @running_timeout_secs::double precision))
+      AND started_at < now() - make_interval(
+          secs => COALESCE(timeout_seconds, @running_timeout_secs)::double precision
+      ))
RETURNING *;
```

### 方案 B：任务心跳

新增 `last_task_heartbeat_at`，daemon 在 agent 执行期间定期上报任务心跳。服务端用最后活跃时间判断是否卡死。

优点：对“长时间但仍活跃”的任务更友好。

缺点：需要新增 API 和 daemon 心跳逻辑，改动范围更大。

## 4. 方案选择

优先选择方案 A。

理由：

1. 改动小：只需 migration、sqlc query、任务创建参数和测试。
2. 向后兼容：未设置 `timeout_seconds` 的历史任务仍使用全局默认值。
3. 风险低：不引入新的高频心跳写入，不增加数据库压力。

方案 B 可作为后续增强，适合云端长任务和付费场景。

## 5. 验证方式

建议新增测试：

1. 创建一个 `running` 任务，`timeout_seconds = 1`，`started_at = now() - 2s`，运行 sweeper 后应转为 `failed`。
2. 创建一个 `running` 任务，`timeout_seconds = NULL`，`started_at` 未超过全局 timeout，运行 sweeper 后不应变化。
3. 创建一个长任务，`timeout_seconds = 20000`，`started_at = now() - 10000s`，运行 sweeper 后不应失败。

## 6. 风险评估

- 数据库迁移风险低：新增 nullable 字段，不影响历史数据。
- 行为风险中等：如果前端或 API 传入过小 timeout，可能导致任务过早失败。因此需要最小值校验，例如不允许小于 60 秒。
- 兼容风险低：默认回退到现有全局 timeout。

## 7. Issue 与 PR 说明

由于当前环境没有登录 GitHub 账号，本交付包未实际提交 Issue 评论和 PR。建议提交时按以下格式：

Issue 评论：

```text
I found that the runtime sweeper uses a global running timeout for all agent tasks.
I plan to add an optional task-level timeout_seconds field and make FailStaleTasks
prefer it over the global fallback. This keeps backward compatibility while making
short and long tasks safer.
```

PR 标题：

```text
fix(tasks): support task-level running timeout in sweeper
```

PR 描述：

```text
## Summary
- add optional timeout_seconds to agent_task_queue
- make FailStaleTasks use per-task timeout with global fallback
- add sweeper tests for short, default, and long task timeout behavior

## Validation
- make test ./server/...

Closes #<issue-id>
```

