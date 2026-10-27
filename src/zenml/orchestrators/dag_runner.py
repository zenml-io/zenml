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

import contextvars
import queue
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from zenml.constants import (
    ENV_ZENML_DAG_RUNNER_WORKER_COUNT,
    handle_int_env_var,
)
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
        shutdown_timeout: float = 30.0,
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
            shutdown_timeout: Maximum seconds to coordinate immediate shutdown.
                A timeout reports incomplete cleanup; running Python threads
                cannot be terminated by the runner.
        """
        self.nodes = {node.id: node for node in nodes}
        self.startup_queue: queue.Queue[Node] = queue.Queue()
        self.node_startup_function = node_startup_function
        self.node_monitoring_function = node_monitoring_function
        self.node_stop_function = node_stop_function
        self.interrupt_function = interrupt_function

        ctx = contextvars.copy_context()
        self.monitoring_thread = threading.Thread(
            name="DagRunner-Monitoring-Loop",
            target=lambda: ctx.run(self._monitoring_loop),
            daemon=True,
        )
        self.monitoring_interval = monitoring_interval
        self.monitoring_delay = monitoring_delay
        self.interrupt_check_interval = interrupt_check_interval
        self.max_parallelism = max_parallelism
        self.shutdown_event = threading.Event()
        self._force_stop_event = threading.Event()
        self._admission_closed = False
        self._state_lock = threading.RLock()
        self._startup_futures: Dict[str, Future[None]] = {}
        self._cleanup_errors: Dict[str, Exception] = {}
        self._monitoring_error: Optional[Exception] = None
        self.shutdown_timeout = shutdown_timeout
        self._stop_executor = ThreadPoolExecutor(
            thread_name_prefix="DagRunner-Stop"
        )
        worker_count = handle_int_env_var(
            ENV_ZENML_DAG_RUNNER_WORKER_COUNT, 10
        )
        self.startup_executor = ThreadPoolExecutor(
            max_workers=worker_count, thread_name_prefix="DagRunner-Startup"
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
        with self._state_lock:
            if self._admission_closed:
                node.status = NodeStatus.CANCELLED
                return
            node.status = NodeStatus.STARTING

        def _start_node_task() -> None:
            if self._force_stop_event.is_set():
                with self._state_lock:
                    node.status = NodeStatus.CANCELLED
                return

            try:
                status = self.node_startup_function(node)
            except Exception:
                status = NodeStatus.FAILED
                logger.exception("Node `%s` failed to start.", node.id)
                if self.node_stop_function is not None:
                    try:
                        self._stop_node(node)
                    except Exception as error:
                        # A lost create response can leave a workload running.
                        # Failed startup is terminal only after cleanup succeeds.
                        self._monitoring_error = error
                        with self._state_lock:
                            self._cleanup_errors[node.id] = error
                        logger.exception(
                            "Cleanup after node `%s` startup failed.", node.id
                        )
                        return

            with self._state_lock:
                force_stop = self._force_stop_event.is_set()
                if not force_stop:
                    node.status = status
            if force_stop:
                # Submission may have succeeded even if its response was lost.
                # The backend identity must be recorded before submission so
                # this pass also handles ambiguous API failures.
                try:
                    self._stop_node(node)
                except Exception as error:
                    with self._state_lock:
                        self._cleanup_errors[node.id] = error
                    logger.exception("Failed stopping node `%s`.", node.id)
                else:
                    with self._state_lock:
                        self._cleanup_errors.pop(node.id, None)
                        node.status = NodeStatus.CANCELLED

        ctx = contextvars.copy_context()
        self._startup_futures[node.id] = self.startup_executor.submit(
            ctx.run, _start_node_task
        )

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

    def _stop_all_nodes(self) -> List[Future[None]]:
        """Start independent cleanup operations for active nodes.

        Returns:
            Futures that complete only after each backend stop has finished.
        """

        def stop(node: Node) -> None:
            try:
                self._stop_node(node)
            except Exception as error:
                with self._state_lock:
                    self._cleanup_errors[node.id] = error
                logger.exception("Failed stopping node `%s`.", node.id)
            else:
                with self._state_lock:
                    self._cleanup_errors.pop(node.id, None)
                    node.status = NodeStatus.CANCELLED

        futures = []
        for node in self.active_nodes:
            ctx = contextvars.copy_context()
            futures.append(self._stop_executor.submit(ctx.run, stop, node))
        return futures

    def _close_admission(self) -> None:
        """Prevent new startup while preserving already admitted nodes."""
        with self._state_lock:
            self._admission_closed = True
            for node in self.nodes.values():
                if node.status in {NodeStatus.NOT_READY, NodeStatus.READY}:
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
                    status = self.node_monitoring_function(node)
                except Exception as error:
                    self._monitoring_error = error
                    logger.exception("Monitoring node `%s` failed.", node.id)
                    return
                else:
                    with self._state_lock:
                        if not self._force_stop_event.is_set():
                            node.status = status
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
        """Run the DAG and drain admitted work after graceful interruption.

        Returns:
            The final node states.

        Raises:
            RuntimeError: If monitoring fails or immediate shutdown cannot be
                confirmed before its deadline.
        """
        self._initialize_startup_queue()
        self.monitoring_thread.start()
        last_interrupt_check = float("-inf")
        shutdown_deadline = None
        try:
            while True:
                if self._monitoring_error is not None:
                    raise RuntimeError(
                        "DAG monitoring failed; workload completion is unknown."
                    ) from self._monitoring_error

                if self.interrupt_function is not None and (
                    time.monotonic() - last_interrupt_check
                    >= self.interrupt_check_interval
                ):
                    interrupt_mode = self.interrupt_function()
                    last_interrupt_check = time.monotonic()
                    if interrupt_mode is not None:
                        self._close_admission()
                    if interrupt_mode == InterruptMode.FORCE:
                        shutdown_deadline = (
                            time.monotonic() + self.shutdown_timeout
                        )
                        with self._state_lock:
                            self._force_stop_event.set()
                        stop_futures = self._stop_all_nodes()
                        _, pending = wait(
                            [*self._startup_futures.values(), *stop_futures],
                            timeout=self.shutdown_timeout,
                        )
                        if pending or self._cleanup_errors:
                            raise RuntimeError(
                                "DAG shutdown is incomplete: "
                                f"{len(pending)} startup/cleanup task(s) remain and "
                                f"{len(self._cleanup_errors)} node(s) could not "
                                "be stopped. Retry immediate stop."
                            )
                        break

                if self._admission_closed:
                    if not self.active_nodes and all(
                        future.done()
                        for future in self._startup_futures.values()
                    ):
                        break
                elif self._process_nodes():
                    break
                self.shutdown_event.wait(0.05)
        finally:
            self._close_admission()
            self.shutdown_event.set()
            self.startup_executor.shutdown(wait=False, cancel_futures=True)
            self._stop_executor.shutdown(wait=False, cancel_futures=True)
            remaining = (
                max(0, shutdown_deadline - time.monotonic())
                if shutdown_deadline is not None
                else self.shutdown_timeout
            )
            self.monitoring_thread.join(timeout=remaining)
            if self.monitoring_thread.is_alive() and sys.exc_info()[0] is None:
                raise RuntimeError(
                    "DAG monitoring did not stop before the shutdown deadline."
                )

        node_statuses = {
            node_id: node.status for node_id, node in self.nodes.items()
        }
        logger.debug("Finished with node statuses: %s", node_statuses)
        return node_statuses
