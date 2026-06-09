#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

# ruff: noqa: D100,D103

import threading
import time

import pytest

from zenml.enums import ExecutionMode
from zenml.orchestrators.monitored_dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)


def test_default_execution_mode_continues_independent_branches() -> None:
    started_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        started_nodes.append(node.id)
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        if node.id == "fails":
            return NodeStatus.FAILED
        return NodeStatus.COMPLETED

    statuses = DagRunner(
        nodes=[
            Node(id="fails"),
            Node(id="depends_on_fails", upstream_nodes=["fails"]),
            Node(id="independent"),
        ],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        monitoring_interval=0.01,
    ).run()

    assert set(started_nodes) == {"fails", "independent"}
    assert statuses == {
        "fails": NodeStatus.FAILED,
        "depends_on_fails": NodeStatus.SKIPPED,
        "independent": NodeStatus.COMPLETED,
    }


def test_continue_on_failure_keeps_starting_independent_branches() -> None:
    started_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        started_nodes.append(node.id)
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        if node.id == "fails":
            return NodeStatus.FAILED
        return NodeStatus.COMPLETED

    statuses = DagRunner(
        nodes=[
            Node(id="fails"),
            Node(id="depends_on_fails", upstream_nodes=["fails"]),
            Node(id="independent"),
        ],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        monitoring_interval=0.01,
        execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
    ).run()

    assert set(started_nodes) == {"fails", "independent"}
    assert statuses == {
        "fails": NodeStatus.FAILED,
        "depends_on_fails": NodeStatus.SKIPPED,
        "independent": NodeStatus.COMPLETED,
    }


def test_stop_on_failure_drains_active_nodes_and_skips_unstarted_work() -> (
    None
):
    failure_reported = threading.Event()
    started_nodes: list[str] = []
    stopped_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        started_nodes.append(node.id)
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        if node.id == "fails":
            failure_reported.set()
            return NodeStatus.FAILED
        if node.id == "active_sibling" and failure_reported.is_set():
            return NodeStatus.COMPLETED
        return NodeStatus.RUNNING

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)

    statuses = DagRunner(
        nodes=[
            Node(id="fails"),
            Node(id="active_sibling"),
            Node(id="queued_independent"),
            Node(id="after_sibling", upstream_nodes=["active_sibling"]),
        ],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        monitoring_interval=0.01,
        max_parallelism=2,
        execution_mode=ExecutionMode.STOP_ON_FAILURE,
    ).run()

    assert set(started_nodes) == {"fails", "active_sibling"}
    assert stopped_nodes == []
    assert statuses == {
        "fails": NodeStatus.FAILED,
        "active_sibling": NodeStatus.COMPLETED,
        "queued_independent": NodeStatus.SKIPPED,
        "after_sibling": NodeStatus.SKIPPED,
    }


def test_stop_on_failure_rechecks_failures_before_starting_ready_nodes() -> (
    None
):
    started_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        started_nodes.append(node.id)
        return NodeStatus.RUNNING

    runner = DagRunner(
        nodes=[Node(id="fails", status=NodeStatus.RUNNING), Node(id="queued")],
        node_startup_function=start_node,
        node_monitoring_function=lambda node: node.status,
        monitoring_interval=0.01,
        execution_mode=ExecutionMode.STOP_ON_FAILURE,
    )
    original_can_start_node = runner._can_start_node

    def fail_during_processing(node: Node) -> bool:
        if node.id == "queued":
            runner.nodes["fails"].status = NodeStatus.FAILED
        return original_can_start_node(node)

    runner._can_start_node = fail_during_processing

    try:
        runner._process_nodes()
    finally:
        runner.startup_executor.shutdown(wait=True)

    assert started_nodes == []
    assert runner.nodes["queued"].status == NodeStatus.SKIPPED


def test_fail_fast_stops_active_nodes_and_cancels_unstarted_work() -> None:
    started_nodes: list[str] = []
    stopped_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        started_nodes.append(node.id)
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        if node.id == "fails":
            return NodeStatus.FAILED
        return NodeStatus.RUNNING

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)

    statuses = DagRunner(
        nodes=[
            Node(id="fails"),
            Node(id="active_sibling"),
            Node(id="queued_independent"),
            Node(
                id="depends_on_queued", upstream_nodes=["queued_independent"]
            ),
        ],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        monitoring_interval=0.01,
        max_parallelism=2,
        execution_mode=ExecutionMode.FAIL_FAST,
    ).run()

    assert set(started_nodes) == {"fails", "active_sibling"}
    assert stopped_nodes == ["active_sibling"]
    assert statuses == {
        "fails": NodeStatus.FAILED,
        "active_sibling": NodeStatus.CANCELLED,
        "queued_independent": NodeStatus.CANCELLED,
        "depends_on_queued": NodeStatus.CANCELLED,
    }


def test_force_stop_keeps_cancelled_status_after_stale_monitor_result() -> (
    None
):
    sibling_stopped = threading.Event()
    stopped_nodes: list[str] = []

    def monitor_node(node: Node) -> NodeStatus:
        if node.id == "fails":
            return NodeStatus.FAILED
        assert sibling_stopped.wait(timeout=5)
        return NodeStatus.RUNNING

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)
        if node.id == "active_sibling":
            sibling_stopped.set()

    statuses = DagRunner(
        nodes=[
            Node(id="fails", status=NodeStatus.RUNNING),
            Node(id="active_sibling", status=NodeStatus.RUNNING),
        ],
        node_startup_function=lambda node: NodeStatus.RUNNING,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        monitoring_interval=0.01,
        max_parallelism=2,
        execution_mode=ExecutionMode.FAIL_FAST,
    ).run()

    assert stopped_nodes == ["active_sibling"]
    assert statuses == {
        "fails": NodeStatus.FAILED,
        "active_sibling": NodeStatus.CANCELLED,
    }


def test_fail_fast_stops_resource_created_by_starting_node() -> None:
    finish_startup = threading.Event()
    stopped_nodes: list[tuple[str, str | None]] = []

    def start_node(node: Node) -> NodeStatus:
        if node.id == "starting_sibling":
            assert finish_startup.wait(timeout=5)
            node.metadata["sandbox_id"] = "created-during-startup"
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        if node.id == "fails":
            finish_startup.set()
            return NodeStatus.FAILED
        return NodeStatus.RUNNING

    def stop_node(node: Node) -> None:
        stopped_nodes.append((node.id, node.metadata.get("sandbox_id")))

    statuses = DagRunner(
        nodes=[Node(id="fails"), Node(id="starting_sibling")],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        monitoring_interval=0.01,
        max_parallelism=2,
        execution_mode=ExecutionMode.FAIL_FAST,
    ).run()

    assert stopped_nodes == [("starting_sibling", "created-during-startup")]
    assert statuses == {
        "fails": NodeStatus.FAILED,
        "starting_sibling": NodeStatus.CANCELLED,
    }


def test_graceful_interrupt_drains_active_nodes_and_cancels_unstarted_work() -> (
    None
):
    active_start_count = 0
    graceful_interrupt_seen = threading.Event()
    started_nodes: list[str] = []
    stopped_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        nonlocal active_start_count
        started_nodes.append(node.id)
        active_start_count += 1
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        if not graceful_interrupt_seen.is_set():
            return NodeStatus.RUNNING
        if node.id == "active_fails":
            return NodeStatus.FAILED
        return NodeStatus.COMPLETED

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)

    def interrupt() -> InterruptMode | None:
        if active_start_count == 2:
            graceful_interrupt_seen.set()
            return InterruptMode.GRACEFUL
        return None

    statuses = DagRunner(
        nodes=[
            Node(id="active_fails"),
            Node(id="active_completes"),
            Node(id="queued"),
            Node(id="not_ready", upstream_nodes=["queued"]),
        ],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
        max_parallelism=2,
        execution_mode=ExecutionMode.FAIL_FAST,
    ).run()

    assert set(started_nodes) == {"active_fails", "active_completes"}
    assert stopped_nodes == []
    assert statuses == {
        "active_fails": NodeStatus.FAILED,
        "active_completes": NodeStatus.COMPLETED,
        "queued": NodeStatus.CANCELLED,
        "not_ready": NodeStatus.CANCELLED,
    }


def test_force_stop_stops_resource_created_by_starting_node() -> None:
    startup_started = threading.Event()
    finish_startup = threading.Event()
    stopped_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        startup_started.set()
        assert finish_startup.wait(timeout=5)
        node.metadata["sandbox_id"] = "sandbox-created-during-startup"
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        return node.status

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)

    def interrupt() -> InterruptMode | None:
        if startup_started.is_set():
            finish_startup.set()
            return InterruptMode.FORCE
        return None

    statuses = DagRunner(
        nodes=[Node(id="train")],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
        max_parallelism=1,
    ).run()

    assert stopped_nodes == ["train"]
    assert statuses == {"train": NodeStatus.CANCELLED}


def test_force_stop_raises_when_late_starting_node_cleanup_fails() -> None:
    startup_started = threading.Event()
    finish_startup = threading.Event()

    def start_node(node: Node) -> NodeStatus:
        startup_started.set()
        assert finish_startup.wait(timeout=5)
        node.metadata["sandbox_id"] = "sandbox-created-during-startup"
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        return node.status

    def stop_node(node: Node) -> None:
        raise RuntimeError("late cleanup failed")

    def interrupt() -> InterruptMode | None:
        if startup_started.is_set():
            finish_startup.set()
            return InterruptMode.FORCE
        return None

    with pytest.raises(RuntimeError, match="late cleanup failed"):
        DagRunner(
            nodes=[Node(id="train")],
            node_startup_function=start_node,
            node_monitoring_function=monitor_node,
            node_stop_function=stop_node,
            interrupt_function=interrupt,
            interrupt_check_interval=0,
            monitoring_interval=0.01,
            max_parallelism=1,
        ).run()


def test_force_stop_times_out_waiting_for_hung_startup() -> None:
    startup_started = threading.Event()
    release_startup = threading.Event()
    stopped_nodes: list[tuple[str, str | None]] = []

    def start_node(node: Node) -> NodeStatus:
        node.metadata["sandbox_id"] = "sandbox-created-before-timeout"
        startup_started.set()
        release_startup.wait(timeout=5)
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        return node.status

    def stop_node(node: Node) -> None:
        stopped_nodes.append((node.id, node.metadata.get("sandbox_id")))

    def interrupt() -> InterruptMode | None:
        if startup_started.is_set():
            return InterruptMode.FORCE
        return None

    runner = DagRunner(
        nodes=[Node(id="train")],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
        max_parallelism=1,
        starting_node_stop_timeout=0.01,
    )

    start_time = time.monotonic()
    try:
        with pytest.raises(RuntimeError, match="Timed out"):
            runner.run()
    finally:
        elapsed = time.monotonic() - start_time
        release_startup.set()
        if future := runner.startup_futures.get("train"):
            future.result(timeout=1)

    assert elapsed < 1
    assert stopped_nodes == [("train", "sandbox-created-before-timeout")]


def test_force_stop_cleans_up_resource_created_after_timeout() -> None:
    startup_started = threading.Event()
    release_startup = threading.Event()
    stopped_nodes: list[tuple[str, str | None]] = []

    def start_node(node: Node) -> NodeStatus:
        startup_started.set()
        release_startup.wait(timeout=5)
        node.metadata["sandbox_id"] = "sandbox-created-after-timeout"
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        return node.status

    def stop_node(node: Node) -> None:
        stopped_nodes.append((node.id, node.metadata.get("sandbox_id")))

    def interrupt() -> InterruptMode | None:
        if startup_started.is_set():
            return InterruptMode.FORCE
        return None

    runner = DagRunner(
        nodes=[Node(id="train")],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
        max_parallelism=1,
        starting_node_stop_timeout=0.01,
    )

    try:
        with pytest.raises(RuntimeError, match="Timed out"):
            runner.run()
    finally:
        release_startup.set()
        if future := runner.startup_futures.get("train"):
            future.result(timeout=1)

    assert stopped_nodes == [("train", "sandbox-created-after-timeout")]


def test_force_stop_attempts_all_running_node_stops_after_error() -> None:
    stopped_nodes: list[str] = []

    def monitor_node(node: Node) -> NodeStatus:
        return node.status

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)
        if node.id == "first":
            raise RuntimeError("stop failed")

    with pytest.raises(RuntimeError, match="first"):
        DagRunner(
            nodes=[
                Node(id="first", status=NodeStatus.RUNNING),
                Node(id="second", status=NodeStatus.RUNNING),
            ],
            node_startup_function=lambda node: NodeStatus.RUNNING,
            node_monitoring_function=monitor_node,
            node_stop_function=stop_node,
            interrupt_function=lambda: InterruptMode.FORCE,
            interrupt_check_interval=0,
            monitoring_interval=0.01,
        ).run()

    assert stopped_nodes == ["first", "second"]


def test_force_stop_cancels_ready_nodes_that_never_started() -> None:
    startup_started = threading.Event()
    finish_startup = threading.Event()
    started_nodes: list[str] = []
    stopped_nodes: list[str] = []

    def start_node(node: Node) -> NodeStatus:
        started_nodes.append(node.id)
        startup_started.set()
        assert finish_startup.wait(timeout=5)
        return NodeStatus.RUNNING

    def monitor_node(node: Node) -> NodeStatus:
        return node.status

    def stop_node(node: Node) -> None:
        stopped_nodes.append(node.id)

    def interrupt() -> InterruptMode | None:
        if startup_started.is_set():
            finish_startup.set()
            return InterruptMode.FORCE
        return None

    statuses = DagRunner(
        nodes=[
            Node(id="train"),
            Node(id="evaluate"),
            Node(id="report", upstream_nodes=["evaluate"]),
        ],
        node_startup_function=start_node,
        node_monitoring_function=monitor_node,
        node_stop_function=stop_node,
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.01,
        max_parallelism=1,
    ).run()

    assert started_nodes == ["train"]
    assert stopped_nodes == ["train"]
    assert statuses == {
        "train": NodeStatus.CANCELLED,
        "evaluate": NodeStatus.CANCELLED,
        "report": NodeStatus.CANCELLED,
    }
