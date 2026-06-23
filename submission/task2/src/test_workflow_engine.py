import unittest

from workflow_engine import CycleError, FailurePolicy, TaskStatus, WorkflowEngine, WorkflowStatus


class WorkflowEngineTest(unittest.TestCase):
    def test_linear_dependency(self):
        engine = WorkflowEngine(max_concurrency=2)
        for task in ["A", "B", "C"]:
            engine.add_task(task)
        engine.add_dependency("A", "B")
        engine.add_dependency("B", "C")

        engine.start()
        self.assertEqual(engine.ready_task_ids(), ["A"])
        engine.complete_task(engine.claim_task("agent-1").id)
        self.assertEqual(engine.ready_task_ids(), ["B"])
        engine.complete_task(engine.claim_task("agent-1").id)
        self.assertEqual(engine.ready_task_ids(), ["C"])
        engine.complete_task(engine.claim_task("agent-1").id)
        self.assertEqual(engine.workflow.status, WorkflowStatus.COMPLETED)

    def test_parallel_dependency(self):
        engine = WorkflowEngine(max_concurrency=2)
        for task in ["A", "B", "C", "D"]:
            engine.add_task(task)
        engine.add_dependency("A", "B")
        engine.add_dependency("A", "C")
        engine.add_dependency("B", "D")
        engine.add_dependency("C", "D")

        engine.start()
        engine.complete_task(engine.claim_task("agent-1").id)
        self.assertEqual(engine.ready_task_ids(), ["B", "C"])
        claimed = {engine.claim_task("agent-1").id, engine.claim_task("agent-2").id}
        self.assertEqual(claimed, {"B", "C"})
        engine.complete_task("B")
        self.assertEqual(engine.ready_task_ids(), [])
        engine.complete_task("C")
        self.assertEqual(engine.ready_task_ids(), ["D"])

    def test_diamond_dependency(self):
        engine = WorkflowEngine(max_concurrency=3)
        for task in ["A", "B", "C", "D"]:
            engine.add_task(task)
        engine.add_dependency("A", "B")
        engine.add_dependency("A", "C")
        engine.add_dependency("B", "D")
        engine.add_dependency("C", "D")
        engine.start()
        engine.complete_task(engine.claim_task("agent-1").id)
        self.assertEqual(engine.ready_task_ids(), ["B", "C"])

    def test_cycle_detection(self):
        engine = WorkflowEngine()
        for task in ["A", "B", "C"]:
            engine.add_task(task)
        engine.add_dependency("A", "B")
        engine.add_dependency("B", "C")
        with self.assertRaises(CycleError):
            engine.add_dependency("C", "A")

    def test_fail_fast_policy(self):
        engine = WorkflowEngine(max_concurrency=2)
        engine.add_task("A", failure_policy=FailurePolicy.FAIL_FAST)
        engine.add_task("B")
        engine.start()
        engine.claim_task("agent-1")
        engine.claim_task("agent-2")
        engine.fail_task("A", "boom")
        self.assertEqual(engine.workflow.status, WorkflowStatus.FAILED)
        self.assertEqual(engine.status_of("B"), TaskStatus.CANCELLED)

    def test_retry_policy(self):
        engine = WorkflowEngine()
        engine.add_task("A", failure_policy=FailurePolicy.RETRY, max_retries=1)
        engine.start()
        engine.claim_task("agent-1")
        engine.fail_task("A", "transient")
        self.assertEqual(engine.status_of("A"), TaskStatus.READY)
        engine.claim_task("agent-1")
        engine.fail_task("A", "still broken")
        self.assertEqual(engine.workflow.status, WorkflowStatus.FAILED)

    def test_skip_policy(self):
        engine = WorkflowEngine(max_concurrency=2)
        engine.add_task("A", failure_policy=FailurePolicy.SKIP)
        engine.add_task("B")
        engine.add_task("C")
        engine.add_dependency("A", "C")
        engine.start()
        engine.claim_task("agent-1")
        engine.claim_task("agent-2")
        engine.fail_task("A", "optional failed")
        self.assertEqual(engine.status_of("A"), TaskStatus.SKIPPED)
        self.assertEqual(engine.status_of("C"), TaskStatus.CANCELLED)
        self.assertEqual(engine.status_of("B"), TaskStatus.RUNNING)
        engine.complete_task("B")
        self.assertEqual(engine.workflow.status, WorkflowStatus.COMPLETED)

    def test_concurrency_limit(self):
        engine = WorkflowEngine(max_concurrency=3)
        for index in range(10):
            engine.add_task(f"T{index}")
        engine.start()
        claimed = [engine.claim_task(f"agent-{index}") for index in range(10)]
        self.assertEqual(len([task for task in claimed if task is not None]), 3)
        self.assertEqual(
            sum(1 for task in engine.workflow.tasks.values() if task.status == TaskStatus.RUNNING),
            3,
        )


if __name__ == "__main__":
    unittest.main()

