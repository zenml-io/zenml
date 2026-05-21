"""Tests for the Kubernetes integration DAG runner."""

from typing import List

from zenml.integrations.kubernetes.orchestrators.dag_runner import (
    DagRunner,
    Node,
    NodeStatus,
)


class _SingleIterationShutdownEvent:
    """Shutdown event that lets the monitoring loop run a limited time."""

    def __init__(self, max_waits: int = 1) -> None:
        self.waits = 0
        self.max_waits = max_waits

    def is_set(self) -> bool:
        """Whether the loop should stop."""
        return self.waits >= self.max_waits

    def wait(self, timeout: float) -> bool:
        """Record the wait call and stop the next iteration."""
        self.waits += 1
        return True


def test_monitoring_loop_calls_iteration_hook_once_with_running_nodes() -> (
    None
):
    """Test that the monitoring hook receives all running nodes once."""
    running_node = Node(id="running", status=NodeStatus.RUNNING)
    completed_node = Node(id="completed", status=NodeStatus.COMPLETED)
    observed_hook_nodes: List[List[str]] = []
    observed_monitor_nodes: List[str] = []

    runner = DagRunner(
        nodes=[running_node, completed_node],
        node_startup_function=lambda node: NodeStatus.RUNNING,
        node_monitoring_function=lambda node: (
            observed_monitor_nodes.append(node.id) or NodeStatus.RUNNING
        ),
        before_monitoring_iteration=lambda nodes: observed_hook_nodes.append(
            [node.id for node in nodes]
        ),
        monitoring_interval=0,
        monitoring_delay=0,
    )
    runner.shutdown_event = _SingleIterationShutdownEvent()  # type: ignore[assignment]

    runner._monitoring_loop()

    assert observed_hook_nodes == [["running"]]
    assert observed_monitor_nodes == ["running"]


def test_monitoring_loop_skips_iteration_hook_without_running_nodes() -> None:
    """Test that the monitoring hook does no work without running nodes."""
    observed_hook_nodes: List[List[str]] = []

    runner = DagRunner(
        nodes=[Node(id="completed", status=NodeStatus.COMPLETED)],
        node_startup_function=lambda node: NodeStatus.RUNNING,
        node_monitoring_function=lambda node: NodeStatus.RUNNING,
        before_monitoring_iteration=lambda nodes: observed_hook_nodes.append(
            [node.id for node in nodes]
        ),
        monitoring_interval=0,
        monitoring_delay=0,
    )
    runner.shutdown_event = _SingleIterationShutdownEvent()  # type: ignore[assignment]

    runner._monitoring_loop()

    assert observed_hook_nodes == []


def test_monitoring_loop_continues_when_iteration_hook_raises(mocker) -> None:
    """Test monitoring hook failures do not stop node monitoring."""
    observed_monitor_nodes: List[str] = []
    debug = mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.dag_runner.logger.debug"
    )

    def failing_hook(nodes: List[Node]) -> None:
        raise RuntimeError("hook failed")

    runner = DagRunner(
        nodes=[Node(id="running", status=NodeStatus.RUNNING)],
        node_startup_function=lambda node: NodeStatus.RUNNING,
        node_monitoring_function=lambda node: (
            observed_monitor_nodes.append(node.id) or NodeStatus.RUNNING
        ),
        before_monitoring_iteration=failing_hook,
        monitoring_interval=0,
        monitoring_delay=0,
    )
    runner.shutdown_event = _SingleIterationShutdownEvent(max_waits=2)  # type: ignore[assignment]

    runner._monitoring_loop()

    hook_failure_debug_calls = [
        call
        for call in debug.call_args_list
        if call.args == ("Failed to run DAG monitoring iteration hook.",)
    ]
    assert len(hook_failure_debug_calls) == 1
    assert hook_failure_debug_calls[0].kwargs == {"exc_info": True}
    assert observed_monitor_nodes == ["running", "running"]
