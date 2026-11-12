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


def _run_dag_interrupted_during_startup(
    interrupt_mode: InterruptMode,
) -> tuple[Dict[str, NodeStatus], List[str]]:
    """Runs a single node DAG that gets interrupted while the node starts.

    The node startup only finishes shortly after the interrupt, so the node is
    still starting when the runner begins to shut down.

    Args:
        interrupt_mode: The interrupt mode to use.

    Returns:
        The final node statuses and the IDs of the stopped nodes.
    """
    startup_started = threading.Event()
    release_startup = threading.Event()
    stopped_node_ids: List[str] = []

    def start_node(node: Node) -> NodeStatus:
        startup_started.set()
        release_startup.wait(timeout=5)
        return NodeStatus.RUNNING

    def interrupt() -> Optional[InterruptMode]:
        if not startup_started.is_set():
            return None
        threading.Timer(0.2, release_startup.set).start()
        return interrupt_mode

    runner = DagRunner(
        nodes=[Node(id="1")],
        node_startup_function=start_node,
        node_monitoring_function=lambda node: node.status,
        node_stop_function=lambda node: stopped_node_ids.append(node.id),
        interrupt_function=interrupt,
        interrupt_check_interval=0,
        monitoring_interval=0.05,
    )
    return runner.run(), stopped_node_ids


def test_dag_runner_force_stop_cancels_starting_nodes():
    """Tests that a force stop also stops nodes that are still starting."""
    node_statuses, stopped_node_ids = _run_dag_interrupted_during_startup(
        InterruptMode.FORCE
    )

    assert stopped_node_ids == ["1"]
    assert node_statuses["1"] == NodeStatus.CANCELLED


def test_dag_runner_waits_for_node_startups_after_interrupt():
    """Tests that node startups don't outlive an interrupted DAG run."""
    node_statuses, stopped_node_ids = _run_dag_interrupted_during_startup(
        InterruptMode.GRACEFUL
    )

    assert stopped_node_ids == []
    assert node_statuses["1"] == NodeStatus.RUNNING
