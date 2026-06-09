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

from zenml.orchestrators.monitored_dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)


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
        nodes=[Node(id="train"), Node(id="evaluate")],
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
    }
