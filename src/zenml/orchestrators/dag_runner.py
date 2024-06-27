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
"""DAG (Directed Acyclic Graph) Runners."""

import threading
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, List

from zenml.logger import get_logger

logger = get_logger(__name__)


def reverse_dag(dag: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Reverse a DAG.

    Args:
        dag: Adjacency list representation of a DAG.

    Returns:
        Adjacency list representation of the reversed DAG.
    """
    reversed_dag = defaultdict(list)

    # Reverse all edges in the graph.
    for node, upstream_nodes in dag.items():
        for upstream_node in upstream_nodes:
            reversed_dag[upstream_node].append(node)

    # Add nodes without incoming edges back in.
    for node in dag:
        if node not in reversed_dag:
            reversed_dag[node] = []

    return reversed_dag


class NodeStatus(Enum):
    """Status of the execution of a node."""

    WAITING = "Waiting"
    RUNNING = "Running"
    COMPLETED = "Completed"


class ThreadedDagRunner:
    """Multi-threaded DAG Runner.

    This class expects a DAG of strings in adjacency list representation, as
    well as a custom `run_fn` as input, then calls `run_fn(node)` for each
    string node in the DAG.

    Steps that can be executed in parallel will be started in separate threads.
    """

    def __init__(
        self,
        dag: Dict[str, List[str]],
        run_fn: Callable[[str], Any],
        parallel_node_startup_waiting_period: float = 0.0,
    ) -> None:
        """Define attributes and initialize all nodes in waiting state.

        Args:
            dag: Adjacency list representation of a DAG.
                E.g.: [(1->2), (1->3), (2->4), (3->4)] should be represented as
                `dag={2: [1], 3: [1], 4: [2, 3]}`
            run_fn: A function `run_fn(node)` that runs a single node
            parallel_node_startup_waiting_period: Delay in seconds to wait in
                between starting parallel nodes.
        """
        self.parallel_node_startup_waiting_period = (
            parallel_node_startup_waiting_period
        )
        self.dag = dag
        self.reversed_dag = reverse_dag(dag)
        self.run_fn = run_fn
        self.nodes = dag.keys()
        self.node_states = {node: NodeStatus.WAITING for node in self.nodes}
        self._lock = threading.Lock()

    def _can_run(self, node: str) -> bool:
        """Determine whether a node is ready to be run.

        This is the case if the node has not run yet and all of its upstream
        node have already completed.

        Args:
            node: The node.

        Returns:
            True if the node can run else False.
        """
        # Check that node has not run yet.
        if not self.node_states[node] == NodeStatus.WAITING:
            return False

        # Check that all upstream nodes of this node have already completed.
        for upstream_node in self.dag[node]:
            if not self.node_states[upstream_node] == NodeStatus.COMPLETED:
                return False

        return True

    def _run_node(self, node: str) -> None:
        """Run a single node.

        Calls the user-defined run_fn, then calls `self._finish_node`.

        Args:
            node: The node.
        """
        self.run_fn(node)
        self._finish_node(node)

    def _run_node_in_thread(self, node: str) -> threading.Thread:
        """Run a single node in a separate thread.

        First updates the node status to running.
        Then calls self._run_node() in a new thread and returns the thread.

        Args:
            node: The node.

        Returns:
            The thread in which the node was run.
        """
        # Update node status to running.
        assert self.node_states[node] == NodeStatus.WAITING
        with self._lock:
            self.node_states[node] = NodeStatus.RUNNING

        # Run node in new thread.
        thread = threading.Thread(target=self._run_node, args=(node,))
        thread.start()
        return thread

    def _finish_node(self, node: str) -> None:
        """Finish a node run.

        First updates the node status to completed.
        Then starts all other nodes that can now be run and waits for them.

        Args:
            node: The node.
        """
        # Update node status to completed.
        assert self.node_states[node] == NodeStatus.RUNNING
        with self._lock:
            self.node_states[node] = NodeStatus.COMPLETED

        # Run downstream nodes.
        threads: List[threading.Thread] = []
        for downstram_node in self.reversed_dag[node]:
            if self._can_run(downstram_node):
                if threads and self.parallel_node_startup_waiting_period > 0:
                    time.sleep(self.parallel_node_startup_waiting_period)

                thread = self._run_node_in_thread(downstram_node)
                threads.append(thread)

        # Wait for all downstream nodes to complete.
        for thread in threads:
            thread.join()

    def run(self) -> None:
        """Call `self.run_fn` on all nodes in `self.dag`.

        The order of execution is determined using topological sort.
        Each node is run in a separate thread to enable parallelism.
        """
        # Run all nodes that can be started immediately.
        # These will, in turn, start other nodes once all of their respective
        # upstream nodes have completed.
        threads: List[threading.Thread] = []
        for node in self.nodes:
            if self._can_run(node):
                if threads and self.parallel_node_startup_waiting_period > 0:
                    time.sleep(self.parallel_node_startup_waiting_period)

                thread = self._run_node_in_thread(node)
                threads.append(thread)

        # Wait till all nodes have completed.
        for thread in threads:
            thread.join()

        # Make sure all nodes were run, otherwise print a warning.
        for node in self.nodes:
            if self.node_states[node] == NodeStatus.WAITING:
                upstream_nodes = self.dag[node]
                logger.warning(
                    f"Node `{node}` was never run, because it was still"
                    f" waiting for the following nodes: `{upstream_nodes}`."
                )
