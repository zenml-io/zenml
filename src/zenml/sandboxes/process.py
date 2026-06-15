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
"""Sandbox process."""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, List, Optional, Tuple

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.sandboxes.session import SandboxSession

logger = get_logger(__name__)

_DEFAULT_COLLECT_CHAR_COUNT = 1_048_576


class SandboxExecError(RuntimeError):
    """Raised when a sandbox command fails to launch."""


@dataclass(frozen=True)
class SandboxOutput:
    """Result of fully consuming a sandbox process."""

    stdout: str
    stderr: str
    exit_code: int
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class SandboxProcess(ABC):
    """Handle to a command being executed inside a sandbox session."""

    def __init__(self, session: "SandboxSession", started_at: float) -> None:
        """Initialize the sandbox process.

        Args:
            session: The owning session.
            started_at: The wall-clock time the process started.
        """
        self._session = session
        self._started_at = started_at
        self._collected = False

    @abstractmethod
    def stdout(self) -> Iterator[str]:
        """Yields stdout lines."""

    @abstractmethod
    def stderr(self) -> Iterator[str]:
        """Yields stderr lines."""

    @abstractmethod
    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the process exits.

        Args:
            timeout: Timeout in seconds to wait.

        Returns:
            The exit code.
        """

    @abstractmethod
    def kill(self) -> None:
        """Terminates the process."""

    @property
    @abstractmethod
    def exit_code(self) -> Optional[int]:
        """Exit code, or `None` if the command is still running."""

    def collect(
        self, *, max_chars: int = _DEFAULT_COLLECT_CHAR_COUNT
    ) -> SandboxOutput:
        """Wait for the process to exit and return the output.

        Args:
            max_chars: Maximum number of characters to collect per stream.

        Raises:
            RuntimeError: If the process output was already collected. The
                streams are drained by the first call, so a second call
                would fabricate an empty result instead of the real output.
            drain_exception: Re-raised from a failed stdout or stderr drain.

        Returns:
            The output of the process.
        """
        if self._collected:
            raise RuntimeError("process output was already collected")

        results: List[Optional[Tuple[str, bool]]] = [None, None]
        errors: List[Optional[BaseException]] = [None, None]

        def _drain(idx: int, stream: Iterator[str]) -> None:
            try:
                results[idx] = _drain_stream(stream, max_chars=max_chars)
            except BaseException as e:  # noqa: BLE001
                errors[idx] = e

        # Drain both streams concurrently to avoid deadlocks. Serial
        # draining deadlocks when a child writes more than one OS pipe
        # buffer (~64KB on Linux) to one stream before the other closes,
        # because the child blocks on write() while we're stuck on the
        # other read().
        stdout_drain_thread = threading.Thread(
            target=_drain, args=(0, self.stdout()), daemon=True
        )
        stderr_drain_thread = threading.Thread(
            target=_drain, args=(1, self.stderr()), daemon=True
        )
        stdout_drain_thread.start()
        stderr_drain_thread.start()
        stdout_drain_thread.join()
        stderr_drain_thread.join()

        # If a drain raised, the corresponding pipe is undrained. wait()
        # below would re-deadlock on a child still writing. Kill the
        # process first, then re-raise the original drain exception.
        drain_exception = errors[0] or errors[1]
        if drain_exception is not None:
            try:
                self.kill()
            except Exception:
                logger.debug(
                    "kill() failed during drain-error cleanup",
                    exc_info=True,
                )

            try:
                self.wait()
            except Exception:
                logger.debug(
                    "wait() failed during drain-error cleanup",
                    exc_info=True,
                )

            raise drain_exception

        stdout, stdout_truncated = results[0] or ("", False)
        stderr, stderr_truncated = results[1] or ("", False)

        exit_code = self.wait()
        self._collected = True
        self._session._log_exec_result(
            exit_code=exit_code, started_at=self._started_at
        )

        return SandboxOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )


def _drain_stream(stream: Iterator[str], max_chars: int) -> Tuple[str, bool]:
    """Drain a stream of lines, capping the returned string at `max_chars`.

    Args:
        stream: Line-delimited string iterator.
        max_chars: Maximum number of characters to collect.

    Returns:
        The joined string and whether it was truncated.
    """
    lines: List[str] = []
    total = 0
    truncated = False
    for line in stream:
        if truncated:
            continue
        total += len(line)
        if total > max_chars:
            truncated = True
            continue
        lines.append(line)

    return "".join(lines), truncated
