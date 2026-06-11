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
"""Future registry for dynamic pipeline execution."""

import threading
import time
from typing import Dict, List, Union

from zenml.execution.pipeline.dynamic.outputs import (
    MapResultsFuture,
    PipelineFuture,
    StepExecutionFuture,
    StepFuture,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class StartupCancelled(Exception):
    """Exception raised when an invocation startup is cancelled."""


class FutureRegistry:
    """Registry for user futures."""

    def __init__(self) -> None:
        """Initialize the future registry."""
        self._lock = threading.RLock()
        self._step_futures: Dict[str, StepFuture] = {}
        self._map_futures: Dict[str, MapResultsFuture] = {}
        self._pipeline_futures: Dict[str, PipelineFuture] = {}

    def register_step_future(
        self,
        invocation_id: str,
        future: StepFuture,
    ) -> StepFuture:
        """Register a step invocation future.

        Args:
            invocation_id: The step invocation ID.
            future: The step future.

        Raises:
            RuntimeError: If a future already exists for the invocation.

        Returns:
            The registered step future.
        """
        with self._lock:
            if invocation_id in self._step_futures:
                raise RuntimeError(
                    f"Step future for invocation `{invocation_id}` already exists."
                )

            self._step_futures[invocation_id] = future
            return future

    def register_map_future(
        self, map_id: str, future: MapResultsFuture
    ) -> MapResultsFuture:
        """Register the future for a map invocation.

        Args:
            map_id: The map ID.
            future: The map future.

        Raises:
            RuntimeError: If a future already exists for the map.

        Returns:
            The registered map future.
        """
        with self._lock:
            if map_id in self._map_futures:
                raise RuntimeError(
                    f"Map future for map `{map_id}` already exists."
                )

            self._map_futures[map_id] = future
            return future

    def get_step_future(self, invocation_id: str) -> StepFuture:
        """Get a step future.

        Args:
            invocation_id: The step invocation ID.

        Raises:
            KeyError: If the future does not exist.

        Returns:
            The step future.
        """
        with self._lock:
            future = self._step_futures.get(invocation_id)
            if future is None:
                raise KeyError(f"Unknown step future `{invocation_id}`.")
            return future

    def get_map_future(self, map_id: str) -> MapResultsFuture:
        """Get a map future.

        Args:
            map_id: The map ID.

        Raises:
            KeyError: If the future does not exist.

        Returns:
            The map future.
        """
        with self._lock:
            future = self._map_futures.get(map_id)
            if future is None:
                raise KeyError(f"Unknown map future `{map_id}`.")
            return future

    def register_pipeline_future(
        self, node_id: str, future: PipelineFuture
    ) -> PipelineFuture:
        """Register a child pipeline future.

        Args:
            node_id: Dependency-graph node ID of the child pipeline call (e.g.
                `pipeline:<name>`), not a pipeline run UUID.
            future: The pipeline future.

        Raises:
            RuntimeError: If a future already exists for the node.

        Returns:
            The registered pipeline future.
        """
        with self._lock:
            if node_id in self._pipeline_futures:
                raise RuntimeError(
                    f"Pipeline future for node `{node_id}` already exists."
                )

            self._pipeline_futures[node_id] = future
            return future

    def get_pipeline_future(self, node_id: str) -> PipelineFuture:
        """Get a child pipeline future.

        Args:
            node_id: Dependency-graph node ID of the child pipeline call.

        Raises:
            KeyError: If the future does not exist.

        Returns:
            The pipeline future.
        """
        with self._lock:
            future = self._pipeline_futures.get(node_id)
            if future is None:
                raise KeyError(f"Unknown pipeline future `{node_id}`.")
            return future

    def bind_step_execution_future(
        self, invocation_id: str, future: StepExecutionFuture
    ) -> None:
        """Bind the step execution future to a step invocation.

        Args:
            invocation_id: The step invocation ID.
            future: The future that represents the started step execution.
        """
        with self._lock:
            step_future = self.get_step_future(invocation_id=invocation_id)
            step_future._set_startup_result(future)

    def rebind_step_execution_future(
        self, invocation_id: str, future: StepExecutionFuture
    ) -> None:
        """Rebind the step execution future to a new attempt of the step.

        Args:
            invocation_id: The step invocation ID.
            future: The future that represents the new step execution attempt.
        """
        with self._lock:
            step_future = self.get_step_future(invocation_id=invocation_id)
            step_future._rebind_execution_future(future)

    def bind_map_child_futures(
        self, map_id: str, child_futures: List[StepFuture]
    ) -> None:
        """Bind expanded child futures to a map.

        Args:
            map_id: The map ID.
            child_futures: The child step futures created for the map.
        """
        with self._lock:
            future = self.get_map_future(map_id=map_id)
            future._set_startup_result(child_futures)

    def set_startup_exception(
        self, invocation_id: str, exception: BaseException
    ) -> None:
        """Set the startup exception for any registered future.

        Args:
            invocation_id: The invocation ID of the future.
            exception: The exception to record on the future.

        Raises:
            KeyError: If no future is registered for `invocation_id`.
        """
        with self._lock:
            for store in (
                self._step_futures,
                self._map_futures,
                self._pipeline_futures,
            ):
                future = store.get(invocation_id)
                if future is not None:
                    future._set_startup_failed(exception)
                    return
            raise KeyError(
                f"No future registered for invocation `{invocation_id}`."
            )

    def get_all_futures(
        self,
    ) -> List[Union[StepFuture, MapResultsFuture, PipelineFuture]]:
        """Return all tracked futures.

        Returns:
            A snapshot of all tracked futures.
        """
        with self._lock:
            return [
                *self._step_futures.values(),
                *self._map_futures.values(),
                *self._pipeline_futures.values(),
            ]

    def await_all_no_raise(self) -> None:
        """Wait for all tracked futures to finish without raising."""
        futures = self.get_all_futures()

        # Poll all futures concurrently before awaiting each of them. This
        # avoids long cumulative waits when individual futures use backoff-based
        # polling internally.
        poll_interval_seconds = 2.0
        while True:
            any_running = False
            for future in futures:
                try:
                    if future.running():
                        any_running = True
                        break
                except Exception:
                    # We still fall back to `wait()` below for this future.
                    continue

            if not any_running:
                break

            time.sleep(poll_interval_seconds)

        for future in futures:
            try:
                future.wait()
            except Exception:
                pass

    def has_in_progress_work(self) -> bool:
        """Check whether any tracked future is still running.

        Returns:
            True if any tracked future is still running, False otherwise.
        """
        return any(future.running() for future in self.get_all_futures())
