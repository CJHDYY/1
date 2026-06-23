# 任务三：开源贡献修复分析报告

## 1. 选择的问题

选择 Multica 官方公开 bug：

- Issue：[#4232 [Bug]: Sub-issue list is not sorted by issue number](https://github.com/multica-ai/multica/issues/4232)
- 现象：先让 Agent 创建一批 sub-issues，再继续追加更多 sub-issues 后，子 issue 列表顺序变乱。
- 期望：sub-issue list 应按 issue number 保持稳定排序。

## 2. 根因分析

源码追踪路径：

```text
packages/core/api/client.ts
  get /api/issues/:id/children

server/internal/handler/issue.go:1634
  h.Queries.ListChildIssues

server/pkg/db/queries/issue.sql:239
  ListChildIssues

server/internal/handler/issue.go:1700
  h.Queries.ListChildrenByParents

server/pkg/db/queries/issue.sql:244
  ListChildrenByParents
```

原始 SQL：

```sql
-- ListChildIssues
SELECT * FROM issue
WHERE parent_issue_id = $1
ORDER BY position ASC, created_at DESC;

-- ListChildrenByParents
SELECT * FROM issue
WHERE workspace_id = sqlc.arg('workspace_id')
  AND parent_issue_id = ANY(sqlc.arg('parent_ids')::uuid[])
ORDER BY parent_issue_id, position ASC, created_at DESC;
```

问题在于：sub-issue 的展示期望是按 issue number 稳定排序，但查询使用 `position ASC, created_at DESC`。当 Agent 分批追加子 issue 时，`position` 可能不能体现 issue number 的自然顺序，`created_at DESC` 又会让后创建的子 issue 排到前面，因此出现“追加后顺序变乱”的现象。

## 3. 修复方案

将单父级和批量父级子 issue 查询统一改成按 issue number 排序：

```sql
-- ListChildIssues
ORDER BY number ASC;

-- ListChildrenByParents
ORDER BY parent_issue_id, number ASC;
```

同步修改 sqlc 生成文件：

- `server/pkg/db/queries/issue.sql`
- `server/pkg/db/generated/issue.sql.go`

## 4. 修复提交

修复已推送到个人 fork：

- Fork：`https://github.com/CJHDYY/multica.git`
- 分支：`fix/sub-issues-sort-by-number`
- Commit：`b9d3a8cc7 fix(issues): sort child issues by number`
- PR 链接：`https://github.com/multica-ai/multica/pull/4468`

核心 diff：

```diff
 SELECT * FROM issue
 WHERE parent_issue_id = $1
-ORDER BY position ASC, created_at DESC;
+ORDER BY number ASC;

 SELECT * FROM issue
 WHERE workspace_id = sqlc.arg('workspace_id')
   AND parent_issue_id = ANY(sqlc.arg('parent_ids')::uuid[])
-ORDER BY parent_issue_id, position ASC, created_at DESC;
+ORDER BY parent_issue_id, number ASC;
```

## 5. 验证方式

建议上游在完整环境中新增/运行以下验证：

1. 创建一个 parent issue。
2. 插入多条 child issues，number 分别为 1、2、3，但 created_at 顺序打乱。
3. 调用 `ListChildIssues`，断言返回顺序为 number ASC。
4. 对多个 parent 调用 `ListChildrenByParents`，断言每个 parent 内部按 number ASC。

## 6. 本地验证情况

当前 Windows 环境缺少上游测试依赖：

```text
go version -> command not found
pnpm --version -> command not found
docker --version -> command not found
```

因此未运行 Multica 的 Go/前端完整测试。已完成的验证：

- 静态检查 diff，确认只改动子 issue 查询排序和对应生成文件。
- 远程确认修复分支已推送到 `CJHDYY/multica.git`。

## 7. 风险评估

- 风险较低：改动只影响 child issue 列表查询排序。
- 行为变化明确：sub-issue 从 position/created_at 排序改为 issue number 排序，符合 #4232 的预期描述。
- 兼容性：API 返回结构不变，仅顺序变化。

## 8. 后续建议

如果产品仍需要支持用户手动拖拽排序，可新增显式排序模式：

- 默认：`number ASC`
- 手动排序：`position ASC`

当前修复优先解决 issue 中描述的“按 issue number 稳定排序”问题。
