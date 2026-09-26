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
"""Pausing the calls to a payload backend that keeps failing."""

import threading
import time
from contextlib import contextmanager
from typing import Iterator

from zenml.exceptions import PayloadStorageUnavailableError
from zenml.logger import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Pauses the calls to a payload backend after repeated failures.

    A backend that hangs holds the thread of each request that calls it for
    the whole timeout, and server threads also serve the requests that need
    no payload storage, such as status updates and heartbeats. After
    `failures_to_pause` failed calls in a row, calls fail at once for `pause`
    seconds. Then a single call goes through as a trial while the others
    still fail at once: its success lets every call through again, and its
    failure pauses the calls again.

    Only failures that retrying may fix count. A missing object or denied
    access means that the backend answered, so it resets the count like a
    success.
    """

    def __init__(
        self, name: str, failures_to_pause: int, pause: float
    ) -> None:
        """Initializes the circuit breaker.

        Args:
            name: The name of the backend, for errors and logs.
            failures_to_pause: The number of failed calls in a row after
                which calls are paused.
            pause: The number of seconds the calls are paused for.
        """
        self._name = name
        self._failures_to_pause = failures_to_pause
        self._pause = pause
        self._failures = 0
        self._paused_until = 0.0
        self._trial_running = False
        self._lock = threading.Lock()

    @contextmanager
    def guard(self) -> Iterator[None]:
        """Guard a call to the backend, which runs in the block.

        Yields:
            Nothing.

        Raises:
            PayloadStorageUnavailableError: If calls to the backend are
                paused.
        """
        with self._lock:
            trial = self._failures >= self._failures_to_pause
            if trial:
                remaining = self._paused_until - time.monotonic()
                if remaining > 0 or self._trial_running:
                    until = (
                        f"for {remaining:.1f} more seconds"
                        if remaining > 0
                        else "while one call checks whether it recovered"
                    )
                    raise PayloadStorageUnavailableError(
                        f"Execution payload storage (`{self._name}`) failed "
                        f"{self._failures} times in a row, so its calls are "
                        f"paused {until}."
                    )
                self._trial_running = True

        failed = False
        try:
            yield
        except PayloadStorageUnavailableError:
            failed = True
            raise
        finally:
            self._record(trial=trial, failed=failed)

    def _record(self, trial: bool, failed: bool) -> None:
        """Record the outcome of a call.

        Args:
            trial: Whether the call was the trial of paused calls.
            failed: Whether the call failed in a way that retrying may fix.
        """
        with self._lock:
            if trial:
                self._trial_running = False
            if not failed:
                if self._failures >= self._failures_to_pause:
                    logger.info(
                        "Execution payload storage (`%s`) recovered, so its "
                        "calls are no longer paused.",
                        self._name,
                    )
                self._failures = 0
                return
            self._failures += 1
            if self._failures >= self._failures_to_pause:
                self._paused_until = time.monotonic() + self._pause
                if self._failures == self._failures_to_pause:
                    logger.warning(
                        "Execution payload storage (`%s`) failed %d times in "
                        "a row, so its calls are paused for %g seconds at a "
                        "time until it recovers.",
                        self._name,
                        self._failures,
                        self._pause,
                    )
