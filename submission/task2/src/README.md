# 多 Agent 任务编排引擎核心实现

运行测试：

```bash
python -m unittest discover -s task2/src -p "test_*.py"
```

实现内容：

- DAG 构建：`add_task()`、`add_dependency()`
- 循环检测：Kahn 拓扑排序
- 调度：`ready_task_ids()`、`claim_task()`
- 状态机：`pending -> ready -> running -> completed/failed/skipped/cancelled`
- 并发控制：`max_concurrency`
- 失败策略：`fail_fast`、`retry`、`skip`

