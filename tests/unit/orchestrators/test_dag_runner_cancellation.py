"""Tests for cancellation of the asynchronous DAG runner."""

import threading
from concurrent.futures import ThreadPoolExecutor

from zenml.orchestrators.dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)


def test_force_stop_revisits_node_cancelled_after_startup_finishes() -> None:
    """Cleanup revisits resources created before the first stop returns."""
    entered = threading.Event()
    release = threading.Event()
    resource_exists = threading.Event()
    stops = []

    def start(node: Node) -> NodeStatus:
        entered.set()
        assert release.wait(2)
        resource_exists.set()
        return NodeStatus.RUNNING

    def stop(node: Node) -> None:
        stops.append(resource_exists.is_set())
        resource_exists.clear()
        if len(stops) == 1:
            release.set()
            # Ensure startup publishes RUNNING before this callback returns
            # and the runner overwrites that status with CANCELLED.
            runner.startup_executor.shutdown(wait=True)
            assert node.status == NodeStatus.RUNNING

    runner = DagRunner(
        [Node(id="step")],
        start,
        lambda node: NodeStatus.RUNNING,
        stop,
        lambda: InterruptMode.FORCE if entered.is_set() else None,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
    )
    try:
        assert runner.run() == {"step": NodeStatus.CANCELLED}
        assert stops == [False, True]
        assert not resource_exists.is_set()
    finally:
        release.set()


def test_force_stop_retains_node_after_monitoring_fails_during_shutdown() -> (
    None
):
    """A monitoring error during shutdown cannot drop a live cleanup target."""
    monitoring = threading.Event()
    stopped = []

    def monitor(node: Node) -> NodeStatus:
        """Fail an in-flight status request after shutdown begins.

        Args:
            node: The node whose workload is still running.

        Raises:
            ConnectionError: The status request failed.
        """
        monitoring.set()
        assert runner.shutdown_event.wait(2)
        raise ConnectionError("The monitoring service is unavailable.")

    runner = DagRunner(
        [Node(id="step", status=NodeStatus.RUNNING)],
        lambda node: NodeStatus.RUNNING,
        monitor,
        lambda node: stopped.append(node.id),
        lambda: InterruptMode.FORCE if monitoring.is_set() else None,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
    )

    assert runner.run() == {"step": NodeStatus.CANCELLED}
    assert "step" in stopped


def test_graceful_stop_drains_starting_node_without_starting_downstream() -> (
    None
):
    """Graceful closes admission while continuing to monitor admitted work."""
    entered = threading.Event()
    stop_requested = threading.Event()
    monitored = threading.Event()
    finish = threading.Event()
    started = []

    def start(node: Node) -> NodeStatus:
        started.append(node.id)
        entered.set()
        assert stop_requested.wait(2)
        return NodeStatus.RUNNING

    def interrupt() -> InterruptMode | None:
        if entered.is_set():
            stop_requested.set()
            return InterruptMode.GRACEFUL
        return None

    def monitor(node: Node) -> NodeStatus:
        monitored.set()
        return NodeStatus.COMPLETED if finish.is_set() else NodeStatus.RUNNING

    runner = DagRunner(
        [Node(id="first"), Node(id="later", upstream_nodes=["first"])],
        start,
        monitor,
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(runner.run)
        try:
            assert monitored.wait(2)
            assert not result.done()
        finally:
            finish.set()
            stop_requested.set()
        assert result.result(timeout=2) == {
            "first": NodeStatus.COMPLETED,
            "later": NodeStatus.CANCELLED,
        }
    assert started == ["first"]


def test_graceful_can_escalate_to_immediate() -> None:
    """Polling continues during drain, allowing a later immediate request."""
    running = threading.Event()
    graceful_seen = threading.Event()
    stopped = threading.Event()

    def start(node: Node) -> NodeStatus:
        running.set()
        return NodeStatus.RUNNING

    def interrupt() -> InterruptMode | None:
        if not running.is_set():
            return None
        if not graceful_seen.is_set():
            graceful_seen.set()
            return InterruptMode.GRACEFUL
        return InterruptMode.FORCE

    runner = DagRunner(
        [Node(id="step")],
        start,
        lambda node: NodeStatus.RUNNING,
        lambda node: stopped.set(),
        interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
    )
    assert runner.run()["step"] == NodeStatus.CANCELLED
    assert graceful_seen.is_set() and stopped.is_set()
