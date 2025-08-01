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
from typing import Any, Callable, Dict, List, Optional

from zenml.enums import ExecutionMode
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

    NOT_STARTED = "not_started"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
        preparation_fn: Optional[Callable[[str], bool]] = None,
        finalize_fn: Optional[Callable[[Dict[str, NodeStatus]], None]] = None,
        parallel_node_startup_waiting_period: float = 0.0,
        max_parallelism: Optional[int] = None,
        continue_fn: Optional[Callable[[], bool]] = None,
        execution_mode: ExecutionMode = ExecutionMode.STOP_ON_FAILURE,
        stop_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Define attributes and initialize all nodes in waiting state.

        Args:
            dag: Adjacency list representation of a DAG.
                E.g.: [(1->2), (1->3), (2->4), (3->4)] should be represented as
                `dag={2: [1], 3: [1], 4: [2, 3]}`
            run_fn: A function `run_fn(node)` that runs a single node
            preparation_fn: A function that is called before the node is run.
                If provided, the function return value determines whether the
                node should be run or can be skipped.
            finalize_fn: A function `finalize_fn(node_states)` that is called
                when all nodes have completed.
            parallel_node_startup_waiting_period: Delay in seconds to wait in
                between starting parallel nodes.
            max_parallelism: Maximum number of nodes to run in parallel
            continue_fn: A function that returns True if the run should continue
                after each step execution, False if it should stop (e.g., due
                to cancellation). If None, execution continues normally.
            execution_mode: The execution mode that determines how failures
                are handled. Defaults to STOP_ON_FAILURE.
            stop_fn: A function `stop_fn(node)` that can stop a running node.
                Required for FAIL_FAST mode to work properly.

        Raises:
            ValueError: If max_parallelism is not greater than 0.
        """
        if max_parallelism is not None and max_parallelism <= 0:
            raise ValueError("max_parallelism must be greater than 0")

        if execution_mode == ExecutionMode.FAIL_FAST and stop_fn is None:
            logger.warning(
                "FAIL_FAST execution mode specified but no stop_fn provided. "
                "Running nodes cannot be stopped on failure and will continue "
                "to completion."
            )

        self.parallel_node_startup_waiting_period = (
            parallel_node_startup_waiting_period
        )
        self.max_parallelism = max_parallelism
        self.dag = dag
        self.reversed_dag = reverse_dag(dag)
        self.run_fn = run_fn
        self.preparation_fn = preparation_fn
        self.finalize_fn = finalize_fn
        self.continue_fn = continue_fn
        self.execution_mode = execution_mode
        self.stop_fn = stop_fn
        self.nodes = dag.keys()
        self.node_states = {
            node: NodeStatus.NOT_STARTED for node in self.nodes
        }
        self._lock = threading.Lock()

        self._stop_requested = False
        self._global_failure = False

    def _can_run(self, node: str) -> bool:
        """Determine whether a node is ready to be run.

        Failed upstream dependencies always prevent downstream nodes from running.

        Args:
            node: The node.

        Returns:
            True if the node can run else False.
        """
        if not self.node_states[node] == NodeStatus.NOT_STARTED:
            return False

        # In FAIL_FAST mode, if any node has failed globally, don't start new nodes
        if (
            self.execution_mode == ExecutionMode.FAIL_FAST
            and self._global_failure
        ):
            return False

        # Check that all upstream nodes of this node have finished.
        for upstream_node in self.dag[node]:
            upstream_status = self.node_states[upstream_node]

            # In all modes, nodes cannot run if direct upstream dependencies failed
            if upstream_status != NodeStatus.COMPLETED:
                return False

        return True

    def _prepare_node_run(self, node: str) -> None:
        """Prepare a node run.

        Args:
            node: The node.
        """
        if self.max_parallelism is None:
            with self._lock:
                self.node_states[node] = NodeStatus.RUNNING
        else:
            while True:
                with self._lock:
                    logger.debug(f"Checking if {node} can run.")
                    running_nodes = len(
                        [
                            state
                            for state in self.node_states.values()
                            if state == NodeStatus.RUNNING
                        ]
                    )
                    if running_nodes < self.max_parallelism:
                        self.node_states[node] = NodeStatus.RUNNING
                        break

                logger.debug(f"Waiting for {running_nodes} nodes to finish.")
                time.sleep(1)

    def _run_node(self, node: str) -> None:
        """Run a single node.

        Calls the user-defined run_fn, then calls `self._finish_node`.

        Args:
            node: The node.
        """
        self._prepare_node_run(node)

        # Check if execution should continue (e.g., check for cancellation)
        if self.continue_fn:
            self._stop_requested = (
                self._stop_requested or not self.continue_fn()
            )
            if self._stop_requested:
                self._finish_node(node, cancelled=True)
                return

        # In FAIL_FAST mode, check for global failure before running
        if (
            self.execution_mode == ExecutionMode.FAIL_FAST
            and self._global_failure
        ):
            self._finish_node(node, cancelled=True)
            return

        if self.preparation_fn:
            run_required = self.preparation_fn(node)
            if not run_required:
                self._finish_node(node)
                return

        try:
            self.run_fn(node)
            self._finish_node(node)
        except Exception as e:
            self._finish_node(node, failed=True)
            logger.exception(f"Node `{node}` failed: {e}")

    def _run_node_in_thread(self, node: str) -> threading.Thread:
        """Run a single node in a separate thread.

        Args:
            node: The node.

        Returns:
            The thread in which the node was run.
        """
        assert self.node_states[node] == NodeStatus.NOT_STARTED
        with self._lock:
            self.node_states[node] = NodeStatus.PENDING

        # Run node in new thread.
        thread = threading.Thread(
            name=node, target=self._run_node, args=(node,)
        )
        thread.start()
        return thread

    def _stop_all_running_nodes(self) -> None:
        """Stop all currently running nodes.

        This is used in FAIL_FAST mode to immediately stop all running nodes
        when a failure occurs.
        """
        if not self.stop_fn:
            logger.warning(
                "stop_fn not provided but FAIL_FAST mode requires it to stop "
                "running nodes. Running nodes will continue to completion."
            )
            return

        with self._lock:
            running_nodes = [
                node
                for node, status in self.node_states.items()
                if status == NodeStatus.RUNNING
            ]

        for node in running_nodes:
            try:
                logger.info(f"Stopping node {node} due to failure elsewhere")
                self.stop_fn(node)
                with self._lock:
                    self.node_states[node] = NodeStatus.CANCELLED
            except Exception as e:
                logger.warning(f"Failed to stop node {node}: {e}")

    def _finish_node(
        self, node: str, failed: bool = False, cancelled: bool = False
    ) -> None:
        """Mark a node as finished and potentially start new nodes.

        Args:
            node: The node to mark as finished.
            failed: Whether the node failed.
            cancelled: Whether the node was cancelled.
        """
        with self._lock:
            if failed:
                self.node_states[node] = NodeStatus.FAILED
            elif cancelled:
                self.node_states[node] = NodeStatus.CANCELLED
            else:
                self.node_states[node] = NodeStatus.COMPLETED

        # Handle different execution modes when a node fails
        if failed:
            if self.execution_mode == ExecutionMode.FAIL_FAST:
                # Set global failure flag and stop all running nodes
                with self._lock:
                    self._global_failure = True
                self._stop_all_running_nodes()
                return
            elif self.execution_mode == ExecutionMode.STOP_ON_FAILURE:
                # Don't run any downstream nodes, but let running nodes continue
                return
            # For CONTINUE_ON_FAILURE, we fall through to start downstream nodes

        # Handle cancellation - always stop processing downstream for cancelled nodes
        if cancelled:
            return

        # Run downstream nodes.
        threads: List[threading.Thread] = []
        for downstream_node in self.reversed_dag[node]:
            if self._can_run(downstream_node):
                if threads and self.parallel_node_startup_waiting_period > 0:
                    time.sleep(self.parallel_node_startup_waiting_period)

                thread = self._run_node_in_thread(downstream_node)
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

        # Call the finalize function.
        if self.finalize_fn:
            self.finalize_fn(self.node_states)

        # Print a status report.
        failed_nodes = []
        skipped_nodes = []
        for node in self.nodes:
            if self.node_states[node] == NodeStatus.FAILED:
                failed_nodes.append(node)
            elif self.node_states[node] == NodeStatus.NOT_STARTED:
                skipped_nodes.append(node)

        if failed_nodes:
            logger.error(
                "The following nodes failed: " + ", ".join(failed_nodes)
            )
        if skipped_nodes:
            logger.warning(
                "The following nodes were not run because they depend on other "
                "nodes that didn't complete: " + ", ".join(skipped_nodes)
            )
        if not failed_nodes and not skipped_nodes:
            logger.info("All nodes completed successfully.")
