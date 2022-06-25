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

from contextlib import ExitStack as does_not_raise
from typing import Dict, List

from zenml.integrations.kubernetes.orchestrators.dag_runner import (
    ThreadedDagRunner,
    reverse_dag,
)


def test_reverse_dag():
    """Test `dag_runner.reverse_dag()`."""
    dag = {1: [7], 2: [], 3: [2, 5], 5: [1, 7], 7: []}
    assert reverse_dag(dag) == {1: [5], 2: [3], 3: [], 5: [3], 7: [1, 5]}


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
    _test_runner(dag={42: []}, correct_results=[42])


def test_dag_runner_linear():  # 5->2->7
    """Test running a linear DAG."""
    _test_runner(dag={2: [5], 5: [], 7: [2]}, correct_results=[91])


def test_dag_runner_multi_path():  # 3->(2, 5)->1
    """Test running a DAG will multiple paths."""
    _test_runner(
        dag={1: [2, 5], 2: [3], 3: [], 5: [3]},
        correct_results=[43, 46],  # 3->5->2->1 or 3->2->5->1
    )


def test_dag_runner_cyclic():
    """Test that nothing happens for cyclic graphs, and no error is raised."""
    _test_runner({1: [2], 2: [1]}, correct_results=[0])
