#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""DAG runner."""

import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class NodeStatus(StrEnum):
    """Status of a DAG node."""

    NOT_READY = "not_ready"  # Can not be started yet
    READY = "ready"  # Can be started but is still waiting in the queue
    STARTING = "starting"  # Is being started, but not yet running
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class InterruptMode(StrEnum):
    """Interrupt mode."""

    GRACEFUL = "graceful"
    FORCE = "force"


class Node(BaseModel):
    """DAG node."""

    id: str
    status: NodeStatus = NodeStatus.NOT_READY
    upstream_nodes: List[str] = []
    metadata: Dict[str, Any] = {}

    @property
    def is_finished(self) -> bool:
        """Whether the node is finished.

        Returns:
            Whether the node is finished.
        """
        return self.status in {
            NodeStatus.COMPLETED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
            NodeStatus.CANCELLED,
        }


class DagRunner:
    """DAG runner.

    This class does the orchestration of running the nodes of a DAG. It is
    running two loops in separate threads:
    The main thread
      - checks if any nodes should be skipped or are ready to
        run, in which case the node will be added to the startup queue
      - creates a worker thread to start the node and executes it in a thread
        pool if there are nodes in the startup queue and the maximum
        parallelism is not reached
      - periodically checks if the DAG should be interrupted
    The monitoring thread
      - monitors the running nodes and updates their status
    """

    def __init__(
        self,
        nodes: List[Node],
        node_startup_function: Callable[[Node], NodeStatus],
        node_monitoring_function: Callable[[Node], NodeStatus],
        node_stop_function: Optional[Callable[[Node], None]] = None,
        interrupt_function: Optional[
            Callable[[], Optional[InterruptMode]]
        ] = None,
        monitoring_interval: float = 1.0,
        monitoring_delay: float = 0.0,
        interrupt_check_interval: float = 1.0,
        max_parallelism: Optional[int] = None,
    ) -> None:
        """Initialize the DAG runner.

        Args:
            nodes: The nodes of the DAG.
            node_startup_function: The function to start a node.
            node_monitoring_function: The function to monitor a node.
            node_stop_function: The function to stop a node.
            interrupt_function: Will be periodically called to check if the
                DAG should be interrupted.
            monitoring_interval: The interval in which the nodes are monitored.
            monitoring_delay: The delay in seconds to wait between monitoring
                different nodes.
            interrupt_check_interval: The interval in which the interrupt
                function is called.
            max_parallelism: The maximum number of nodes to run in parallel.
        """
        self.nodes = {node.id: node for node in nodes}
        self.startup_queue: queue.Queue[Node] = queue.Queue()
        self.node_startup_function = node_startup_function
        self.node_monitoring_function = node_monitoring_function
        self.node_stop_function = node_stop_function
        self.interrupt_function = interrupt_function
        self.monitoring_thread = threading.Thread(
            name="DagRunner-Monitoring-Loop",
            target=self._monitoring_loop,
            daemon=True,
        )
        self.monitoring_interval = monitoring_interval
        self.monitoring_delay = monitoring_delay
        self.interrupt_check_interval = interrupt_check_interval
        self.max_parallelism = max_parallelism
        self.shutdown_event = threading.Event()
        self.startup_executor = ThreadPoolExecutor(
            max_workers=10, thread_name_prefix="DagRunner-Startup"
        )

    @property
    def running_nodes(self) -> List[Node]:
        """Running nodes.

        Returns:
            Running nodes.
        """
        return [
            node
            for node in self.nodes.values()
            if node.status == NodeStatus.RUNNING
        ]

    @property
    def active_nodes(self) -> List[Node]:
        """Active nodes.

        Active nodes are nodes that are either running or starting.

        Returns:
            Active nodes.
        """
        return [
            node
            for node in self.nodes.values()
            if node.status in {NodeStatus.RUNNING, NodeStatus.STARTING}
        ]

    def _initialize_startup_queue(self) -> None:
        """Initialize the startup queue.

        The startup queue contains all nodes that are ready to be started.
        """
        for node in self.nodes.values():
            if node.status in {NodeStatus.READY, NodeStatus.STARTING}:
                self.startup_queue.put(node)

    def _can_start_node(self, node: Node) -> bool:
        """Check if a node can be started.

        Args:
            node: The node to check.

        Returns:
            Whether the node can be started.
        """
        return all(
            self.nodes[upstream_node_id].status == NodeStatus.COMPLETED
            for upstream_node_id in node.upstream_nodes
        )

    def _should_skip_node(self, node: Node) -> bool:
        """Check if a node should be skipped.

        Args:
            node: The node to check.

        Returns:
            Whether the node should be skipped.
        """
        return any(
            self.nodes[upstream_node_id].status
            in {NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.CANCELLED}
            for upstream_node_id in node.upstream_nodes
        )

    def _start_node(self, node: Node) -> None:
        """Start a node.

        This will start of a thread that will run the startup function.

        Args:
            node: The node to start.
        """
        node.status = NodeStatus.STARTING

        def _start_node_task() -> None:
            if self.shutdown_event.is_set():
                logger.debug(
                    "Cancelling startup of node `%s` because shutdown was "
                    "requested.",
                    node.id,
                )
                return

            try:
                node.status = self.node_startup_function(node)
            except Exception:
                node.status = NodeStatus.FAILED
                logger.exception("Node `%s` failed to start.", node.id)
            else:
                logger.info(
                    "Node `%s` started (status: %s)", node.id, node.status
                )

        self.startup_executor.submit(_start_node_task)

    def _stop_node(self, node: Node) -> None:
        """Stop a node.

        Args:
            node: The node to stop.

        Raises:
            RuntimeError: If the node stop function is not set.
        """
        if not self.node_stop_function:
            raise RuntimeError("Node stop function is not set.")

        self.node_stop_function(node)

    def _stop_all_nodes(self) -> None:
        """Stop all running nodes."""
        for node in self.running_nodes:
            self._stop_node(node)
            node.status = NodeStatus.CANCELLED

    def _process_nodes(self) -> bool:
        """Process the nodes.

        This method will check if any nodes should be skipped or are ready to
        run, in which case the node will be added to the startup queue.

        Returns:
            Whether the DAG is finished.
        """
        finished = True

        for node in self.nodes.values():
            if node.status == NodeStatus.NOT_READY:
                if self._should_skip_node(node):
                    node.status = NodeStatus.SKIPPED
                    logger.warning(
                        "Skipping node `%s` because upstream node failed.",
                        node.id,
                    )
                elif self._can_start_node(node):
                    node.status = NodeStatus.READY
                    self.startup_queue.put(node)

            if not node.is_finished:
                finished = False

        # Start nodes until we reach the maximum configured parallelism
        max_parallelism = self.max_parallelism or len(self.nodes)
        while len(self.active_nodes) < max_parallelism:
            try:
                node = self.startup_queue.get_nowait()
            except queue.Empty:
                break
            else:
                self.startup_queue.task_done()
                self._start_node(node)

        return finished

    def _monitoring_loop(self) -> None:
        """Monitoring loop.

        This should run in a separate thread and monitors the running nodes.
        """
        while not self.shutdown_event.is_set():
            start_time = time.time()
            for node in self.running_nodes:
                try:
                    node.status = self.node_monitoring_function(node)
                except Exception:
                    node.status = NodeStatus.FAILED
                    logger.exception("Node `%s` failed.", node.id)
                else:
                    logger.debug(
                        "Node `%s` status updated to `%s`",
                        node.id,
                        node.status,
                    )
                    if node.status == NodeStatus.FAILED:
                        logger.error("Node `%s` failed.", node.id)
                    elif node.status == NodeStatus.COMPLETED:
                        logger.info("Node `%s` completed.", node.id)

                time.sleep(self.monitoring_delay)

            duration = time.time() - start_time
            time_to_sleep = max(0, self.monitoring_interval - duration)
            self.shutdown_event.wait(timeout=time_to_sleep)

    def run(self) -> Dict[str, NodeStatus]:
        """Run the DAG.

        Returns:
            The final node states.
        """
        self._initialize_startup_queue()

        self.monitoring_thread.start()

        interrupt_mode = None
        last_interrupt_check = time.time()

        while True:
            if self.interrupt_function is not None:
                if (
                    time.time() - last_interrupt_check
                    >= self.interrupt_check_interval
                ):
                    if interrupt_mode := self.interrupt_function():
                        logger.warning("DAG execution interrupted.")
                        break
                    last_interrupt_check = time.time()

            is_finished = self._process_nodes()
            if is_finished:
                break

            time.sleep(0.5)

        self.shutdown_event.set()
        if interrupt_mode == InterruptMode.FORCE:
            # If a force interrupt was requested, we stop all running nodes.
            self._stop_all_nodes()

        self.monitoring_thread.join()

        node_statuses = {
            node_id: node.status for node_id, node in self.nodes.items()
        }
        logger.debug("Finished with node statuses: %s", node_statuses)

        return node_statuses
