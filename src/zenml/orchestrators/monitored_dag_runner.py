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
"""Run DAG nodes and monitor the backend resources they create."""

import contextvars
import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

from zenml.constants import (
    ENV_ZENML_DAG_RUNNER_WORKER_COUNT,
    handle_int_env_var,
)
from zenml.enums import ExecutionMode
from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)

STARTING_NODE_STOP_TIMEOUT_SECONDS = 30.0


class NodeStatus(StrEnum):
    """Status of a DAG node."""

    NOT_READY = "not_ready"
    READY = "ready"
    STARTING = "starting"
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
    """Start DAG nodes and monitor their backend resources."""

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
        starting_node_stop_timeout: float = STARTING_NODE_STOP_TIMEOUT_SECONDS,
        execution_mode: ExecutionMode = ExecutionMode.CONTINUE_ON_FAILURE,
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
            starting_node_stop_timeout: Seconds to wait for a starting node to
                finish startup during force-stop cleanup.
            execution_mode: The ZenML execution mode to apply after node
                failures are observed.
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
        self.starting_node_stop_timeout = starting_node_stop_timeout
        self.execution_mode = execution_mode
        self.shutdown_event = threading.Event()
        self._node_state_lock = threading.RLock()
        self._disabled_new_start_status: Optional[NodeStatus] = None
        self._force_stop_requested = False
        self._stop_attempted_node_ids: set[str] = set()
        self._stop_errors: List[str] = []
        worker_count = handle_int_env_var(
            ENV_ZENML_DAG_RUNNER_WORKER_COUNT, 10
        )
        self.startup_executor = ThreadPoolExecutor(
            max_workers=worker_count, thread_name_prefix="DagRunner-Startup"
        )
        self.startup_futures: Dict[str, Future[None]] = {}

    @property
    def running_nodes(self) -> List[Node]:
        """Return nodes that are currently running."""
        return [
            node
            for node in self.nodes.values()
            if node.status == NodeStatus.RUNNING
        ]

    @property
    def active_nodes(self) -> List[Node]:
        """Return nodes that are running or starting."""
        return [
            node
            for node in self.nodes.values()
            if node.status in {NodeStatus.RUNNING, NodeStatus.STARTING}
        ]

    def _initialize_startup_queue(self) -> None:
        """Queue nodes that are ready to start."""
        for node in self.nodes.values():
            if node.status in {NodeStatus.READY, NodeStatus.STARTING}:
                self.startup_queue.put(node)

    def _can_start_node(self, node: Node) -> bool:
        """Return whether all upstream nodes completed."""
        return all(
            self.nodes[upstream_node_id].status == NodeStatus.COMPLETED
            for upstream_node_id in node.upstream_nodes
        )

    def _should_skip_node(self, node: Node) -> bool:
        """Return whether any upstream node ended unsuccessfully."""
        return any(
            self.nodes[upstream_node_id].status
            in {NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.CANCELLED}
            for upstream_node_id in node.upstream_nodes
        )

    def _start_node(self, node: Node) -> None:
        """Submit a node startup task to the executor."""
        with self._node_state_lock:
            if self.shutdown_event.is_set():
                node.status = NodeStatus.CANCELLED
                return

            node.status = NodeStatus.STARTING

        def _start_node_task() -> None:
            if self.shutdown_event.is_set():
                logger.debug(
                    "Cancelling startup of node `%s` because shutdown was "
                    "requested.",
                    node.id,
                )
                with self._node_state_lock:
                    node.status = NodeStatus.CANCELLED
                return

            try:
                status = self.node_startup_function(node)
            except Exception:
                with self._node_state_lock:
                    node.status = NodeStatus.FAILED
                logger.exception("Node `%s` failed to start.", node.id)
            else:
                if (
                    self._force_stop_requested
                    and self.shutdown_event.is_set()
                    and status == NodeStatus.RUNNING
                ):
                    with self._node_state_lock:
                        node.status = NodeStatus.RUNNING
                    self._stop_node_after_interrupt(node)
                    return

                with self._node_state_lock:
                    node.status = status
                logger.info(
                    "Node `%s` started (status: %s)", node.id, node.status
                )

        ctx = contextvars.copy_context()
        self.startup_futures[node.id] = self.startup_executor.submit(
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

    def _disable_new_starts(
        self, unstarted_node_terminal_status: NodeStatus
    ) -> None:
        """Prevent new node starts and finish unstarted nodes."""
        if self._disabled_new_start_status is not None:
            return

        self._disabled_new_start_status = unstarted_node_terminal_status
        self._finish_unstarted_nodes(unstarted_node_terminal_status)

    def _finish_unstarted_nodes(self, status: NodeStatus) -> None:
        """Mark nodes that have not created backend resources as terminal."""
        while True:
            try:
                node = self.startup_queue.get_nowait()
            except queue.Empty:
                break
            self.startup_queue.task_done()
            if node.status == NodeStatus.READY:
                node.status = status

        for node in self.nodes.values():
            if node.status in {NodeStatus.NOT_READY, NodeStatus.READY}:
                node.status = status

    def _cancel_queued_nodes(self) -> None:
        """Cancel nodes that never started."""
        self._finish_unstarted_nodes(NodeStatus.CANCELLED)

    def _apply_failure_policy(self) -> None:
        """Apply the configured execution mode after a node failure."""
        if self._disabled_new_start_status is not None:
            return
        if not any(
            node.status == NodeStatus.FAILED for node in self.nodes.values()
        ):
            return

        if self.execution_mode == ExecutionMode.STOP_ON_FAILURE:
            logger.info(
                "Disabling new DAG node starts after a node failure. Active "
                "nodes will continue because execution mode is `%s`.",
                self.execution_mode,
            )
            self._disable_new_starts(NodeStatus.SKIPPED)
        elif self.execution_mode == ExecutionMode.FAIL_FAST:
            logger.info(
                "Force-stopping active DAG nodes after a node failure because "
                "execution mode is `%s`.",
                self.execution_mode,
            )
            self._disable_new_starts(NodeStatus.CANCELLED)
            self._force_stop_requested = True

    def _record_stop_error(self, message: str) -> None:
        """Record an error that should make the DAG runner fail."""
        with self._node_state_lock:
            self._stop_errors.append(message)

    def _stop_node_after_interrupt(self, node: Node) -> None:
        """Stop one node after an interrupt and record stop errors."""
        # The check and the add must be atomic: the main thread and a startup
        # worker can both reach this for the same node during a force stop,
        # and only one of them may call the stop function.
        with self._node_state_lock:
            if node.id in self._stop_attempted_node_ids:
                node.status = NodeStatus.CANCELLED
                return
            self._stop_attempted_node_ids.add(node.id)
        try:
            self._stop_node(node)
        except Exception as e:
            self._record_stop_error(f"Failed to stop node `{node.id}`: {e}")
            logger.exception("Failed to stop node `%s`.", node.id)
        else:
            with self._node_state_lock:
                node.status = NodeStatus.CANCELLED

    def _stop_starting_nodes(self) -> bool:
        """Stop nodes whose startup function may have created resources.

        Returns:
            Whether waiting for any startup future timed out.
        """
        startup_stop_timed_out = False
        for node in list(self.nodes.values()):
            if node.status != NodeStatus.STARTING:
                continue

            future = self.startup_futures.get(node.id)
            if future and future.cancel():
                node.status = NodeStatus.CANCELLED
                continue

            if future:
                try:
                    future.result(timeout=self.starting_node_stop_timeout)
                except TimeoutError:
                    startup_stop_timed_out = True
                    message = (
                        "Timed out after "
                        f"{self.starting_node_stop_timeout} seconds waiting "
                        f"for node `{node.id}` to finish startup during "
                        "force stop. ZenML could not confirm whether a "
                        "backend resource was created or stopped."
                    )
                    self._record_stop_error(message)
                    logger.error(message)
                    if self.node_stop_function and node.metadata:
                        self._stop_node_after_interrupt(node)
                    if not node.is_finished:
                        node.status = NodeStatus.CANCELLED
                    continue
                except Exception:
                    node.status = NodeStatus.FAILED
                    logger.exception(
                        "Startup future for node `%s` failed.", node.id
                    )

            if node.status == NodeStatus.RUNNING:
                self._stop_node_after_interrupt(node)
            elif not node.is_finished:
                node.status = NodeStatus.CANCELLED

        return startup_stop_timed_out

    def _stop_all_nodes(self) -> Tuple[bool, List[str]]:
        """Stop nodes that are running or still starting.

        Returns:
            Whether waiting for any startup future timed out, followed by all
            errors recorded while stopping nodes.
        """
        self._cancel_queued_nodes()
        startup_stop_timed_out = self._stop_starting_nodes()
        for node in self.running_nodes:
            self._stop_node_after_interrupt(node)
        return startup_stop_timed_out, self._stop_errors

    def _process_nodes(self) -> bool:
        """Queue ready nodes, skip blocked nodes, and return completion."""
        # Other threads (startup workers, the monitoring thread) acquire the
        # node state lock before writing node statuses, and the remaining
        # writers run on this thread. Statuses therefore cannot change while
        # this method holds the lock, so applying the failure policy once on
        # entry is sufficient; failures observed later are handled by the
        # next call.
        with self._node_state_lock:
            self._apply_failure_policy()

            finished = True

            for node in self.nodes.values():
                if (
                    self._disabled_new_start_status is None
                    and node.status == NodeStatus.NOT_READY
                ):
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

            if self._disabled_new_start_status is not None:
                return finished

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
        """Monitor running nodes until shutdown is requested."""
        while not self.shutdown_event.is_set():
            start_time = time.time()
            with self._node_state_lock:
                running_nodes = self.running_nodes

            for node in running_nodes:
                try:
                    status = self.node_monitoring_function(node)
                except Exception:
                    status = NodeStatus.FAILED
                    logger.exception("Node `%s` failed.", node.id)

                with self._node_state_lock:
                    if node.status != NodeStatus.RUNNING:
                        continue
                    node.status = status

                logger.debug(
                    "Node `%s` status updated to `%s`",
                    node.id,
                    status,
                )
                if status == NodeStatus.FAILED:
                    logger.error("Node `%s` failed.", node.id)
                elif status == NodeStatus.COMPLETED:
                    logger.info("Node `%s` completed.", node.id)

                time.sleep(self.monitoring_delay)

            duration = time.time() - start_time
            time_to_sleep = max(0, self.monitoring_interval - duration)
            self.shutdown_event.wait(timeout=time_to_sleep)

    def run(self) -> Dict[str, NodeStatus]:
        """Run the DAG.

        Raises:
            RuntimeError: If one or more nodes could not be stopped during a
                force stop, so their backend resources may still be running.

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
                    interrupt_mode = self.interrupt_function()
                    if interrupt_mode == InterruptMode.FORCE:
                        logger.warning("DAG execution force interrupted.")
                        self._force_stop_requested = True
                        break
                    if (
                        interrupt_mode == InterruptMode.GRACEFUL
                        and self._disabled_new_start_status is None
                    ):
                        logger.warning("DAG execution gracefully interrupted.")
                        self._disable_new_starts(NodeStatus.CANCELLED)
                    last_interrupt_check = time.time()

            is_finished = self._process_nodes()
            if is_finished or self._force_stop_requested:
                break

            time.sleep(0.5)

        force_stop_requested = (
            interrupt_mode == InterruptMode.FORCE or self._force_stop_requested
        )
        with self._node_state_lock:
            self._stop_errors = []
        self.shutdown_event.set()
        startup_stop_timed_out = False
        stop_errors: List[str] = []
        if force_stop_requested:
            startup_stop_timed_out, stop_errors = self._stop_all_nodes()

        self.monitoring_thread.join()
        # If a startup future already exceeded the force-stop timeout, waiting
        # here would recreate the unbounded wait that force stop avoids.
        self.startup_executor.shutdown(
            wait=not startup_stop_timed_out,
            cancel_futures=startup_stop_timed_out,
        )

        if stop_errors:
            raise RuntimeError(
                "Failed to stop all DAG nodes: " + "; ".join(stop_errors)
            )

        node_statuses = {
            node_id: node.status for node_id, node in self.nodes.items()
        }
        logger.debug("Finished with node statuses: %s", node_statuses)

        return node_statuses
