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
from typing import Dict, List, Union

from zenml.execution.pipeline.dynamic.outputs import (
    MapResultsFuture,
    StepExecutionFuture,
    StepFuture,
)


class StartupCancelled(Exception):
    """Exception raised when an invocation startup is cancelled."""


class FutureRegistry:
    """Registry for user futures."""

    def __init__(self) -> None:
        """Initialize the future registry."""
        self._lock = threading.RLock()
        self._step_futures: Dict[str, StepFuture] = {}
        self._map_futures: Dict[str, MapResultsFuture] = {}

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

    def fail_step_startup(
        self, invocation_id: str, exception: BaseException
    ) -> None:
        """Store a startup failure for a step invocation.

        Args:
            invocation_id: The step invocation ID.
            exception: The startup exception.
        """
        with self._lock:
            future = self.get_step_future(invocation_id=invocation_id)
            future._set_startup_failed(exception)

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

    def fail_map_startup(self, map_id: str, exception: BaseException) -> None:
        """Store a startup failure for a map.

        Args:
            map_id: The map ID.
            exception: The startup exception.
        """
        with self._lock:
            future = self.get_map_future(map_id=map_id)
            future._set_startup_failed(exception)

    def _get_all_futures(self) -> List[Union[StepFuture, MapResultsFuture]]:
        """Return all tracked futures.

        Returns:
            The tracked futures.
        """
        with self._lock:
            return [
                *self._step_futures.values(),
                *self._map_futures.values(),
            ]

    def await_all(self) -> None:
        """Wait for all tracked futures to finish."""
        for future in self._get_all_futures():
            future.wait()

    def has_in_progress_work(self) -> bool:
        """Check whether any tracked future is still running.

        Returns:
            True if any tracked future is still running, False otherwise.
        """
        return any(future.running() for future in self._get_all_futures())

    def cancel_step_startup(self, invocation_id: str) -> None:
        """Cancel startup for a specific step invocation.

        Args:
            invocation_id: The step invocation ID.
        """
        with self._lock:
            step_future = self.get_step_future(invocation_id=invocation_id)
            step_future._cancel_startup(
                StartupCancelled(
                    f"Startup for step `{invocation_id}` was cancelled."
                )
            )

    def cancel_map_startup(self, map_id: str) -> None:
        """Cancel startup for a specific map expansion.

        Args:
            map_id: The map ID.
        """
        with self._lock:
            map_future = self.get_map_future(map_id=map_id)
            map_future._cancel_startup(
                StartupCancelled(
                    f"Startup for map expansion `{map_id}` was cancelled."
                )
            )
