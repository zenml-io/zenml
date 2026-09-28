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
    `failure_threshold` failed calls in a row, calls fail at once for
    `recovery_timeout_seconds`. Then a single trial call goes through while
    the others still fail at once: its success lets every call through
    again, and its failure pauses the calls again.

    It guards each backend call, which may load or store many blobs. Only
    failures that retrying may fix count: a missing object
    (`FileNotFoundError`) or denied access (`PermissionError`) means that the
    backend answered, so it resets the count like a success.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int,
        recovery_timeout_seconds: float,
    ) -> None:
        """Initializes the circuit breaker.

        Args:
            name: The name of the backend, for errors and logs.
            failure_threshold: The number of failed calls in a row after
                which calls are paused.
            recovery_timeout_seconds: The number of seconds calls fail at once
                before one trial call.
        """
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout_seconds = recovery_timeout_seconds
        self._consecutive_failures = 0
        self._paused_until = 0.0
        self._trial_in_progress = False
        self._lock = threading.Lock()

    @contextmanager
    def guard(self) -> Iterator[None]:
        """Guard a call to the backend, which runs in the block.

        Yields:
            Nothing.

        Raises:
            PayloadStorageUnavailableError: If calls to the backend are
                paused.
            FileNotFoundError: If the object of the call is missing, which
                resets the count like a success.
            PermissionError: If access was denied, which resets the count
                like a success.
            Exception: Any other error of the call, which counts as a
                failure.
        """
        with self._lock:
            trial = self._consecutive_failures >= self._failure_threshold
            if trial:
                remaining = self._paused_until - time.monotonic()
                if remaining > 0 or self._trial_in_progress:
                    until = (
                        f"for {remaining:.1f} more seconds"
                        if remaining > 0
                        else "while one call checks whether it recovered"
                    )
                    raise PayloadStorageUnavailableError(
                        f"Execution payload storage (`{self._name}`) failed "
                        f"{self._consecutive_failures} times in a row, so its "
                        f"calls are paused {until}."
                    )
                self._trial_in_progress = True

        failed = False
        try:
            yield
        except (FileNotFoundError, PermissionError):
            raise
        except Exception:
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
                self._trial_in_progress = False
            if not failed:
                if self._consecutive_failures >= self._failure_threshold:
                    logger.info(
                        "Execution payload storage (`%s`) recovered, so its "
                        "calls are no longer paused.",
                        self._name,
                    )
                self._consecutive_failures = 0
                return
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._paused_until = (
                    time.monotonic() + self._recovery_timeout_seconds
                )
                if self._consecutive_failures == self._failure_threshold:
                    logger.warning(
                        "Execution payload storage (`%s`) failed %d times in "
                        "a row, so its calls are paused for %g seconds at a "
                        "time until it recovers.",
                        self._name,
                        self._consecutive_failures,
                        self._recovery_timeout_seconds,
                    )
