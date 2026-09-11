#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import threading
from contextlib import ExitStack as does_not_raise
from typing import Dict, List, Optional

from zenml.orchestrators.dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)
from zenml.orchestrators.legacy_dag_runner import (
    ThreadedDagRunner,
    reverse_dag,
)


def test_reverse_dag():
    """Test `legacy_dag_runner.reverse_dag()`."""
    dag = {"1": ["7"], "2": [], "3": ["2", "5"], "5": ["1", "7"], "7": []}
    assert reverse_dag(dag) == {
        "1": ["5"],
        "2": ["3"],
        "3": [],
        "5": ["3"],
        "7": ["1", "5"],
    }


class MockRunFn:
    """Stateful function that iteratively does `r=(r+1)*f(x)`."""

    def __init__(self) -> None:
        self.result = 0

    def __call__(self, node) -> None:
        self.result = (self.result + 1) * int(node)


def _test_runner(dag: Dict[str, List[str]], correct_results: List[int]):
    """Utility function to test running a given DAG."""
    run_fn = MockRunFn()
    with does_not_raise():
        ThreadedDagRunner(dag, run_fn).run()
    assert run_fn.result in correct_results


def test_dag_runner_empty():  # {}
    """Test running a DAG with no nodes."""
    _test_runner(dag={}, correct_results=[0])


def test_dag_runner_single():  # 42
    """Test running a DAG with a single node."""
    _test_runner(dag={"42": []}, correct_results=[42])


def test_dag_runner_linear():  # 5->2->7
    """Test running a DAG with a linear DAG."""
    _test_runner(dag={"2": ["5"], "5": [], "7": ["2"]}, correct_results=[91])


def test_dag_runner_multi_path():  # 3->(2, 5)->1
    """Test running a DAG will multiple paths."""
    _test_runner(
        dag={"1": ["2", "5"], "2": ["3"], "3": [], "5": ["3"]},
        correct_results=[43, 46],  # 3->5->2->1 or 3->2->5->1
    )


def test_dag_runner_cyclic():
    """Test that nothing happens for cyclic graphs, and no error is raised."""
    _test_runner({"1": ["2"], "2": ["1"]}, correct_results=[0])


def test_dag_runner_stop_all_nodes_cancels_starting_node():
    """A force stop must also cancel a node whose startup is still running.

    Regression test: `_stop_all_nodes` used to only look at nodes with
    status RUNNING. A node whose startup function had already passed the
    shutdown check but not yet returned was left out, so it was never
    stopped, kept its underlying resource alive, and could later flip to
    RUNNING after the force stop had already finished.
    """
    stopped_ids: List[str] = []

    def noop_fn(node: Node) -> NodeStatus:
        return node.status

    def stop_fn(node: Node) -> None:
        stopped_ids.append(node.id)

    runner = DagRunner(
        nodes=[Node(id="1"), Node(id="2")],
        node_startup_function=noop_fn,
        node_monitoring_function=noop_fn,
        node_stop_function=stop_fn,
    )
    runner.nodes["1"].status = NodeStatus.STARTING
    runner.nodes["2"].status = NodeStatus.RUNNING

    runner._stop_all_nodes()

    assert set(stopped_ids) == {"1", "2"}
    assert runner.nodes["1"].status == NodeStatus.CANCELLED
    assert runner.nodes["2"].status == NodeStatus.CANCELLED


def test_dag_runner_force_stop_waits_for_late_starting_node():
    """A force stop should also cancel a node that only just started.

    End to end regression test for the race where a node's startup task has
    already passed the shutdown check and is still creating its underlying
    resource when the force stop happens. Once the startup task finishes and
    flips the node to RUNNING, the runner must stop and cancel it too instead
    of leaving it running after `run()` has already returned.
    """
    started = threading.Event()
    release = threading.Event()
    stopped_ids: List[str] = []

    def startup_fn(node: Node) -> NodeStatus:
        started.set()
        release.wait(timeout=5)
        return NodeStatus.RUNNING

    def monitoring_fn(node: Node) -> NodeStatus:
        return node.status

    def stop_fn(node: Node) -> None:
        stopped_ids.append(node.id)

    def interrupt_fn() -> Optional[InterruptMode]:
        return InterruptMode.FORCE if started.is_set() else None

    runner = DagRunner(
        nodes=[Node(id="1")],
        node_startup_function=startup_fn,
        node_monitoring_function=monitoring_fn,
        node_stop_function=stop_fn,
        interrupt_function=interrupt_fn,
        interrupt_check_interval=0,
        monitoring_interval=0.05,
    )

    # Release the blocked startup function only once the force stop has
    # actually run its first pass, so the node is still STARTING at that
    # point and only flips to RUNNING afterwards, regardless of wall clock
    # timing.
    original_stop_all_nodes = runner._stop_all_nodes
    stop_all_nodes_calls = 0

    def wrapped_stop_all_nodes() -> None:
        nonlocal stop_all_nodes_calls
        stop_all_nodes_calls += 1
        original_stop_all_nodes()
        if stop_all_nodes_calls == 1:
            release.set()

    runner._stop_all_nodes = wrapped_stop_all_nodes  # type: ignore[method-assign]

    statuses = runner.run()

    assert stopped_ids
    assert all(node_id == "1" for node_id in stopped_ids)
    assert statuses["1"] == NodeStatus.CANCELLED
