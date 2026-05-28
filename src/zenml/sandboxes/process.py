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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

# Default cap for ``SandboxProcess.collect`` — 1 Mi*characters* per stream
# (counted via ``len(line)`` on the decoded UTF-8 string, so it's actually
# a code-point count, not a byte count). 1 Mi covers typical agent tool
# output (a printed answer, an exception traceback, a small dataframe
# dump) without swamping the LLM's context window.
_DEFAULT_COLLECT_CHARS = 1_048_576


class SandboxExecError(RuntimeError):
    """Raised when a sandbox command fails to launch.

    Once a ``SandboxProcess`` has been returned by ``exec()``, runtime errors
    flow through ``exit_code`` / ``stderr()`` instead of this exception.
    """


@dataclass(frozen=True)
class SandboxOutput:
    """Result of fully consuming a ``SandboxProcess``.

    Returned by ``SandboxProcess.collect()``. Carries both stdout and
    stderr as captured strings plus the exit code, along with per-stream
    truncation flags so callers can tell when they hit the character
    cap. Frozen so callers can't mutate the captured strings in place —
    if they want to append a truncation marker for downstream display,
    they assemble a local string and pass it on.
    """

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
    """

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
        """Exit code, or ``None`` if the command is still running."""

    def collect(
        self, *, max_chars: int = _DEFAULT_COLLECT_CHARS
    ) -> SandboxOutput:
        """Fully drains stdout + stderr, blocks until exit, returns everything.

        This is the typical convenience for agent-tool callers: replaces
        the ``stdout = ...; stderr = ...; code = wait()`` dance with one
        call that returns a ``SandboxOutput``. Both streams are drained
        to completion (so ``wait()`` is safe to call even when the
        underlying provider holds output in a buffered reader); once the
        cap is hit on a stream, subsequent whole lines are dropped (no
        partial lines emitted) and the corresponding ``*_truncated`` flag
        is set.

        For full streaming control, iterate ``stdout()`` / ``stderr()``
        directly instead.

        Note: blocks indefinitely on ``wait()``. If you need a wall-clock
        bound, iterate the streams yourself and call ``kill()`` on
        timeout.

        Args:
            max_chars: Soft cap per stream, counted by ``len(line)`` on
                the decoded text (i.e. code points). Default 1 Mi. A
                single line larger than the cap is dropped entirely —
                we never emit partial lines.

        Returns:
            A ``SandboxOutput`` with captured stdout, stderr, exit code,
            and per-stream truncation flags.
        """
        stdout, stdout_truncated = _drain_capped(self.stdout(), max_chars)
        stderr, stderr_truncated = _drain_capped(self.stderr(), max_chars)
        exit_code = self.wait()
        return SandboxOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )


def _drain_capped(stream: Iterator[str], max_chars: int) -> Tuple[str, bool]:
    """Drain a line iterator fully, capping the returned string at ``max_chars``.

    Always consumes to completion (StopIteration) so the underlying
    provider's wait() is not blocked. Lines that would push the total
    over ``max_chars`` are dropped, but iteration continues.

    Args:
        stream: Source iterator (line-delimited strings).
        max_chars: Soft cap on the returned string length (in
            characters, not bytes — counted via ``len(line)``).

    Returns:
        Tuple of ``(joined_string, truncated_flag)``.
    """
    parts: List[str] = []
    total = 0
    truncated = False
    for line in stream:
        total += len(line)
        if total > max_chars:
            truncated = True
            continue
        parts.append(line)
    return "".join(parts), truncated
