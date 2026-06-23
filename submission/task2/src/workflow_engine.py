from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FailurePolicy(str, Enum):
    FAIL_FAST = "fail_fast"
    RETRY = "retry"
    SKIP = "skip"


TERMINAL_TASK_STATUS = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.SKIPPED,
    TaskStatus.CANCELLED,
}


@dataclass
class TaskNode:
    id: str
    name: str | None = None
    failure_policy: FailurePolicy = FailurePolicy.FAIL_FAST
    max_retries: int = 0
    timeout_seconds: int | None = None
    condition: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    assigned_agent: str | None = None
    output: Any = None
    error: str | None = None


@dataclass
class Workflow:
    id: str
    max_concurrency: int
    status: WorkflowStatus = WorkflowStatus.DRAFT
    tasks: dict[str, TaskNode] = field(default_factory=dict)
    dependencies: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    dependents: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


class WorkflowError(Exception):
    pass


class CycleError(WorkflowError):
    pass


class WorkflowEngine:
    def __init__(self, workflow_id: str = "workflow", max_concurrency: int = 1):
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.workflow = Workflow(id=workflow_id, max_concurrency=max_concurrency)

    def add_task(
        self,
        task_id: str,
        *,
        name: str | None = None,
        failure_policy: FailurePolicy = FailurePolicy.FAIL_FAST,
        max_retries: int = 0,
        timeout_seconds: int | None = None,
        condition: str | None = None,
    ) -> None:
        if task_id in self.workflow.tasks:
            raise WorkflowError(f"task already exists: {task_id}")
        self.workflow.tasks[task_id] = TaskNode(
            id=task_id,
            name=name or task_id,
            failure_policy=failure_policy,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            condition=condition,
        )

    def add_dependency(self, before: str, after: str) -> None:
        self._require_task(before)
        self._require_task(after)
        if before == after:
            raise CycleError("self dependency is not allowed")
        self.workflow.dependencies[after].add(before)
        self.workflow.dependents[before].add(after)
        try:
            self.detect_cycle()
        except CycleError:
            self.workflow.dependencies[after].remove(before)
            self.workflow.dependents[before].remove(after)
            raise

    def detect_cycle(self) -> None:
        indegree = {task_id: 0 for task_id in self.workflow.tasks}
        for task_id, deps in self.workflow.dependencies.items():
            indegree[task_id] += len(deps)

        queue = deque([task_id for task_id, degree in indegree.items() if degree == 0])
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for child in self.workflow.dependents[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if visited != len(self.workflow.tasks):
            raise CycleError("workflow contains a cycle")

    def start(self) -> None:
        if self.workflow.status != WorkflowStatus.DRAFT:
            raise WorkflowError("workflow can only be started from draft")
        self.detect_cycle()
        self.workflow.status = WorkflowStatus.RUNNING
        self._refresh_ready_tasks()

    def claim_task(self, agent_id: str) -> TaskNode | None:
        if self.workflow.status != WorkflowStatus.RUNNING:
            return None
        self._refresh_ready_tasks()
        if self._running_count() >= self.workflow.max_concurrency:
            return None

        for task in sorted(self.workflow.tasks.values(), key=lambda item: item.id):
            if task.status == TaskStatus.READY:
                task.status = TaskStatus.RUNNING
                task.assigned_agent = agent_id
                task.attempts += 1
                return task
        return None

    def complete_task(self, task_id: str, output: Any = None) -> None:
        task = self._require_task(task_id)
        if task.status != TaskStatus.RUNNING:
            raise WorkflowError(f"task {task_id} is not running")
        task.status = TaskStatus.COMPLETED
        task.output = output
        task.assigned_agent = None
        self._refresh_ready_tasks()
        self._refresh_workflow_status()

    def fail_task(self, task_id: str, error: str = "") -> None:
        task = self._require_task(task_id)
        if task.status != TaskStatus.RUNNING:
            raise WorkflowError(f"task {task_id} is not running")
        task.error = error
        task.assigned_agent = None

        if task.failure_policy == FailurePolicy.RETRY and task.attempts <= task.max_retries:
            task.status = TaskStatus.READY
            return

        if task.failure_policy == FailurePolicy.SKIP:
            task.status = TaskStatus.SKIPPED
            self._cancel_blocked_dependents(task.id)
            self._refresh_ready_tasks()
            self._refresh_workflow_status()
            return

        task.status = TaskStatus.FAILED
        self._fail_fast(error or f"task {task_id} failed")

    def cancel_workflow(self) -> None:
        self.workflow.status = WorkflowStatus.CANCELLED
        for task in self.workflow.tasks.values():
            if task.status not in TERMINAL_TASK_STATUS:
                task.status = TaskStatus.CANCELLED

    def ready_task_ids(self) -> list[str]:
        self._refresh_ready_tasks()
        return sorted(task.id for task in self.workflow.tasks.values() if task.status == TaskStatus.READY)

    def status_of(self, task_id: str) -> TaskStatus:
        return self._require_task(task_id).status

    def _require_task(self, task_id: str) -> TaskNode:
        try:
            return self.workflow.tasks[task_id]
        except KeyError as exc:
            raise WorkflowError(f"task not found: {task_id}") from exc

    def _running_count(self) -> int:
        return sum(1 for task in self.workflow.tasks.values() if task.status == TaskStatus.RUNNING)

    def _deps_completed(self, task_id: str) -> bool:
        return all(self.workflow.tasks[dep].status == TaskStatus.COMPLETED for dep in self.workflow.dependencies[task_id])

    def _refresh_ready_tasks(self) -> None:
        if self.workflow.status != WorkflowStatus.RUNNING:
            return
        free_slots = self.workflow.max_concurrency - self._running_count()
        if free_slots <= 0:
            return
        for task in sorted(self.workflow.tasks.values(), key=lambda item: item.id):
            if free_slots <= 0:
                break
            if task.status == TaskStatus.PENDING and self._deps_completed(task.id):
                task.status = TaskStatus.READY
                free_slots -= 1

    def _refresh_workflow_status(self) -> None:
        if self.workflow.status != WorkflowStatus.RUNNING:
            return
        statuses = [task.status for task in self.workflow.tasks.values()]
        if all(status in {TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.CANCELLED} for status in statuses):
            self.workflow.status = WorkflowStatus.COMPLETED
        elif any(status == TaskStatus.FAILED for status in statuses):
            self.workflow.status = WorkflowStatus.FAILED

    def _fail_fast(self, error: str) -> None:
        self.workflow.status = WorkflowStatus.FAILED
        for task in self.workflow.tasks.values():
            if task.status in {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING}:
                task.status = TaskStatus.CANCELLED
                task.error = error

    def _cancel_blocked_dependents(self, skipped_task_id: str) -> None:
        queue = deque(self.workflow.dependents[skipped_task_id])
        while queue:
            task_id = queue.popleft()
            task = self.workflow.tasks[task_id]
            if task.status in TERMINAL_TASK_STATUS:
                continue
            task.status = TaskStatus.CANCELLED
            task.error = f"dependency {skipped_task_id} was skipped"
            queue.extend(self.workflow.dependents[task_id])

