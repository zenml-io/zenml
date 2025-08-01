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
        }


class DagRunner:
    """DAG runner."""

    def __init__(
        self,
        nodes: List[Node],
        startup_function: Callable[[Node], NodeStatus],
        monitoring_function: Callable[[Node], NodeStatus],
        interrupt_function: Optional[Callable[[], bool]] = None,
        monitoring_interval: float = 1.0,
        max_parallelism: Optional[int] = None,
    ) -> None:
        """Initialize the DAG runner.

        Args:
            nodes: The nodes of the DAG.
            startup_function: The function to start a node.
            monitoring_function: The function to monitor a node.
            interrupt_function: Will be periodically called to check if the
                DAG should be interrupted.
            monitoring_interval: The interval in which the nodes are monitored.
            max_parallelism: The maximum number of nodes to run in parallel.
        """
        self.nodes = {node.id: node for node in nodes}
        self.startup_queue: queue.Queue[Node] = queue.Queue()
        self.startup_function = startup_function
        self.monitoring_function = monitoring_function
        self.interrupt_function = interrupt_function
        self.startup_thread = threading.Thread(
            name="DagRunner-Startup-Loop",
            target=self._startup_loop,
            daemon=True,
        )
        self.monitoring_thread = threading.Thread(
            name="DagRunner-Monitoring-Loop",
            target=self._monitoring_loop,
            daemon=True,
        )
        self.monitoring_interval = monitoring_interval
        self.max_parallelism = max_parallelism
        self.shutdown_event = threading.Event()
        self.startup_executor = ThreadPoolExecutor(
            max_workers=10, thread_name_prefix="DagRunner-Startup-Worker"
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
            in {NodeStatus.FAILED, NodeStatus.SKIPPED}
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
            try:
                node.status = self.startup_function(node)
            except Exception:
                node.status = NodeStatus.FAILED
                logger.exception("Node `%s` failed to start.", node.id)
            else:
                logger.info(
                    "Node `%s` started (status: %s)", node.id, node.status
                )

        self.startup_executor.submit(_start_node_task)

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

        return finished

    def _monitoring_loop(self) -> None:
        """Monitoring loop.

        This should run in a separate thread and monitors the running nodes.
        """
        while not self.shutdown_event.is_set():
            start_time = time.time()
            for node in self.running_nodes:
                try:
                    node.status = self.monitoring_function(node)
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

            duration = time.time() - start_time
            time_to_sleep = max(0, self.monitoring_interval - duration)
            self.shutdown_event.wait(timeout=time_to_sleep)

    def _startup_loop(self) -> None:
        """Startup loop.

        This should run in a separate thread and starts nodes that are ready to
        run.
        """
        while not self.shutdown_event.is_set():
            if self.max_parallelism is not None:
                if len(self.active_nodes) >= self.max_parallelism:
                    # Sleep for 0.5 seconds or exit immediately if the shutdown
                    # event was set
                    logger.debug(
                        "Maximum amount of nodes running (%s), waiting for 0.5 "
                        "seconds.",
                        self.max_parallelism,
                    )
                    self.shutdown_event.wait(timeout=0.5)
                    continue

            try:
                node = self.startup_queue.get(timeout=0.5)
            except queue.Empty:
                pass
            else:
                self.startup_queue.task_done()
                self._start_node(node)

    def run(self) -> Dict[str, NodeStatus]:
        """Run the DAG.

        Returns:
            The final node states.
        """
        self._initialize_startup_queue()

        self.startup_thread.start()
        self.monitoring_thread.start()

        while True:
            if self.interrupt_function is not None:
                if self.interrupt_function():
                    break

            is_finished = self._process_nodes()
            if is_finished:
                break

            time.sleep(0.5)

        self.shutdown_event.set()

        self.startup_thread.join()
        self.monitoring_thread.join()

        node_statuses = {
            node_id: node.status for node_id, node in self.nodes.items()
        }
        logger.debug("Finished with node statuses: %s", node_statuses)

        return node_statuses
