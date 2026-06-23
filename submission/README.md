# 全栈研发工程师综合笔试题提交说明

## 交付概览

本提交包围绕 Multica 开源项目完成四部分内容：

1. 任务一：深度代码考古
   - `task1/setup-log.md`
   - `task1/fault-analysis.md`
2. 任务二：多 Agent 任务编排引擎
   - `task2/design-doc.md`
   - `task2/src/workflow_engine.py`
   - `task2/src/test_workflow_engine.py`
3. 任务三：开源贡献
   - `task3/fix-report.md`
   - `task3/pr-link.txt`
4. 任务四：AI 工作流
   - `task4/ai-configs/`
   - `task4/ai-usage.md`

## 源码分析对象

- 仓库：`https://github.com/multica-ai/multica`
- 分析 commit：`45dae3185f01cdcd60967df82ca12c16917e566a`
- 重点模块：
  - `server/internal/daemon`
  - `server/internal/handler/daemon.go`
  - `server/internal/service/task.go`
  - `server/pkg/db/queries/agent.sql`
  - `server/cmd/server/runtime_sweeper.go`

## 任务二运行方式

在提交目录根目录执行：

```bash
python -m unittest discover -s task2/src -p "test_*.py"
```

本地已运行结果：

```text
Ran 8 tests in 0.002s

OK
```

## 开源修复提交

- Fork 仓库：`https://github.com/CJHDYY/multica.git`
- 修复分支：`fix/sub-issues-sort-by-number`
- 修复 commit：`b9d3a8cc7 fix(issues): sort child issues by number`
- PR 创建入口：`https://github.com/multica-ai/multica/compare/main...CJHDYY:multica:fix/sub-issues-sort-by-number?quick_pull=1`

## 重要说明

- `task1/setup-log.md` 记录了本机环境检查结果：当前机器缺少 Docker、Go、pnpm、make，因此未能真实启动 Multica 全栈服务。
- `task3/` 包含已推送到 fork 的真实修复分支信息、GitHub 权限检查日志和修复分析。
- 任务二核心实现是可运行代码，未依赖第三方库。
