"""Tests for cancellation of the asynchronous DAG runner."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from zenml.orchestrators.dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)


def test_force_stop_cleans_up_startup_completing_after_first_stop() -> None:
    """A submission completing during stop receives a second cleanup pass."""
    entered = threading.Event()
    release = threading.Event()
    created = threading.Event()
    stops = []

    def start(node: Node) -> NodeStatus:
        entered.set()
        assert release.wait(2)
        created.set()
        return NodeStatus.RUNNING

    def stop(node: Node) -> None:
        stops.append(created.is_set())
        release.set()

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
        assert True in stops
    finally:
        release.set()


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


def test_incomplete_startup_shutdown_raises_and_cleans_late_resource() -> None:
    """A bounded wait never claims an unresolved submission was terminated."""
    entered = threading.Event()
    release = threading.Event()
    created = threading.Event()
    late_cleanup = threading.Event()

    def start(node: Node) -> NodeStatus:
        entered.set()
        assert release.wait(2)
        created.set()
        return NodeStatus.RUNNING

    def stop(node: Node) -> None:
        if created.is_set():
            late_cleanup.set()

    runner = DagRunner(
        [Node(id="step")],
        start,
        lambda node: NodeStatus.RUNNING,
        stop,
        lambda: InterruptMode.FORCE if entered.is_set() else None,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
        shutdown_timeout=0.02,
    )
    try:
        with pytest.raises(RuntimeError, match="shutdown is incomplete"):
            runner.run()
    finally:
        release.set()
    assert late_cleanup.wait(2)


def test_monitor_error_is_reported_instead_of_silently_finishing() -> None:
    """Failure of a monitoring callback reaches the runner's caller."""

    def monitor(node: Node) -> NodeStatus:
        raise ValueError("monitor unavailable")

    runner = DagRunner(
        [Node(id="step")],
        lambda node: NodeStatus.RUNNING,
        monitor,
        monitoring_interval=0.01,
    )
    with pytest.raises(RuntimeError, match="completion is unknown"):
        runner.run()


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_ambiguous_startup_failure_requires_cleanup(
    cleanup_fails: bool,
) -> None:
    """A lost create response cannot turn a still-running workload terminal."""
    stopped = []

    def start(node: Node) -> NodeStatus:
        node.metadata["job_name"] = "possibly-created"
        raise TimeoutError("create response lost")

    def stop(node: Node) -> None:
        stopped.append(node.metadata["job_name"])
        if cleanup_fails:
            raise RuntimeError("provider unavailable")

    runner = DagRunner(
        [Node(id="step")],
        start,
        lambda node: NodeStatus.RUNNING,
        stop,
        monitoring_interval=0.01,
    )
    if cleanup_fails:
        with pytest.raises(RuntimeError, match="completion is unknown"):
            runner.run()
    else:
        assert runner.run() == {"step": NodeStatus.FAILED}
    assert stopped == ["possibly-created"]
