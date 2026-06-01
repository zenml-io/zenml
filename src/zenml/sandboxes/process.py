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
"""Process abstraction for sandbox-executed commands."""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, List, Optional, Tuple

if TYPE_CHECKING:
    from zenml.sandboxes.session import SandboxSession

# Default cap for `SandboxProcess.collect`: 1 Mi characters per stream
# (counted via `len(line)` on the decoded UTF-8 string, so it's actually
# a code-point count, not a byte count). 1 Mi covers typical agent tool
# output (a printed answer, an exception traceback, a small dataframe
# dump) without swamping the LLM's context window.
_DEFAULT_COLLECT_CHARS = 1_048_576


class SandboxExecError(RuntimeError):
    """Raised when a sandbox command fails to launch.

    Once a `SandboxProcess` has been returned by `exec()`, runtime errors
    flow through `exit_code` / `stderr()` instead of this exception.
    """


@dataclass(frozen=True)
class SandboxOutput:
    """Result of fully consuming a sandbox process."""

    stdout: str
    stderr: str
    exit_code: int
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class SandboxProcess(ABC):
    """Handle to a running command inside a Session.

    Output streams are line-delimited iterators of decoded UTF-8 text. A
    trailing line without a newline is yielded once the underlying reader
    closes. Binary-stream consumers should use a different abstraction.

    Flavor subclasses may populate `_session` and `_started_at` so
    `collect()` can emit a per-exec exit-code + duration marker into
    the session's sandbox log. Both default to `None` for processes
    constructed outside a session context (rare, mostly test paths).
    """

    _session: Optional["SandboxSession"] = None
    _started_at: Optional[float] = None
    _collected: bool = False

    @abstractmethod
    def stdout(self) -> Iterator[str]:
        """Yields stdout one line at a time as the command produces output."""

    @abstractmethod
    def stderr(self) -> Iterator[str]:
        """Yields stderr one line at a time as the command produces output."""

    @abstractmethod
    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the command finishes and returns the exit code."""

    @abstractmethod
    def kill(self) -> None:
        """Terminates this command. Safe to call after the process exits."""

    @property
    @abstractmethod
    def exit_code(self) -> Optional[int]:
        """Exit code, or `None` if the command is still running."""

    def collect(
        self, *, max_chars: int = _DEFAULT_COLLECT_CHARS
    ) -> SandboxOutput:
        """Fully drains stdout + stderr, blocks until exit, returns everything.

        Both streams are drained concurrently in daemon threads. Serial
        draining deadlocks when a child writes more than one OS pipe
        buffer (~64KB on Linux) to one stream before the other closes,
        because the child blocks on write() while we're stuck on the
        other read(). Once the cap is hit on a stream, subsequent whole
        lines are dropped and the `*_truncated` flag is set.

        For full streaming control, iterate `stdout()` / `stderr()`
        directly instead, but drain both concurrently or the same
        pipe-buffer deadlock applies.

        Calling `collect()` more than once on the same process returns
        a fresh `SandboxOutput` but emits the exec-result log marker
        only on the first call (the streams are already drained on
        subsequent calls, so the captured strings are empty).

        Note: blocks indefinitely on `wait()`. If you need a wall-clock
        bound, iterate the streams yourself and call `kill()` on
        timeout.

        Args:
            max_chars: Soft cap per stream, counted by `len(line)` on
                the decoded text (i.e. code points). Default 1 Mi. A
                single line larger than the cap is dropped entirely.
                We never emit partial lines.

        Returns:
            A `SandboxOutput` with captured stdout, stderr, exit code,
            and per-stream truncation flags.
        """
        results: List[Optional[Tuple[str, bool]]] = [None, None]

        def _drain(idx: int, stream: Iterator[str]) -> None:
            results[idx] = _drain_capped(stream, max_chars)

        t_out = threading.Thread(
            target=_drain, args=(0, self.stdout()), daemon=True
        )
        t_err = threading.Thread(
            target=_drain, args=(1, self.stderr()), daemon=True
        )
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()
        stdout, stdout_truncated = results[0] or ("", False)
        stderr, stderr_truncated = results[1] or ("", False)

        exit_code = self.wait()
        if self._session is not None and not self._collected:
            self._collected = True
            self._session._log_exec_result(
                exit_code=exit_code,
                started_at=self._started_at,
            )
        return SandboxOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )


def _drain_capped(stream: Iterator[str], max_chars: int) -> Tuple[str, bool]:
    """Drain a line iterator fully, capping the returned string at `max_chars`.

    Always consumes to completion (StopIteration) so the underlying
    provider's wait() is not blocked. Once the running total of captured
    characters would exceed `max_chars`, no further lines are appended
    and the `truncated` flag is set. Iteration continues so the pipe
    drains.

    Args:
        stream: Source iterator (line-delimited strings).
        max_chars: Soft cap on the returned string length (in
            characters, not bytes, counted via `len(line)`).

    Returns:
        Tuple of `(joined_string, truncated_flag)`.
    """
    parts: List[str] = []
    total = 0
    truncated = False
    for line in stream:
        if truncated:
            continue
        total += len(line)
        if total > max_chars:
            truncated = True
            continue
        parts.append(line)
    return "".join(parts), truncated
