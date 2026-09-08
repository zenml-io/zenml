"""Persistent FIFO Bash using public sandbox APIs and bounded controller waits.

Closing a process stream is not proof that remote descendants stopped. The
session owner must destroy the sandbox before collecting output for grading.
"""

from __future__ import annotations

import base64
import queue
import re
import shlex
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from zenml.sandboxes.process import SandboxProcess
from zenml.sandboxes.session import SandboxSession

MAX_OUTPUT = 256 * 1024
_FRAME_BYTES = 4096
_FRAME_LINE_LIMIT = 5500
_FRAMER = """import base64, sys
while True:
    chunk = sys.stdin.buffer.read1(4096)
    if not chunk:
        break
    sys.stdout.buffer.write(base64.b64encode(chunk) + b"\\n")
    sys.stdout.buffer.flush()
"""
_T = TypeVar("_T")


class SandboxShell:
    """Keep one Bash process alive without requiring a public stdin API."""

    def __init__(
        self,
        session: SandboxSession,
        command_timeout: float,
        episode_timeout: float,
    ) -> None:
        """Configure a shell inside an already allocated session.

        Args:
            session: Caller-owned sandbox session.
            command_timeout: Total seconds for one command, including transfer.
            episode_timeout: Shell lifetime in seconds, including startup.

        Raises:
            ValueError: A timeout is not positive.
        """
        if command_timeout <= 0 or episode_timeout <= 0:
            raise ValueError("Shell timeouts must be positive")
        self.session = session
        self.command_timeout = command_timeout
        self.episode_timeout = episode_timeout
        self.stopped = False
        self._started = False
        self._deadline = 0.0
        self._control = "/tmp/endless-shell-" + uuid.uuid4().hex
        self._process: SandboxProcess | None = None
        self._output: queue.Queue[bytes] = queue.Queue(maxsize=1024)
        self._queued_bytes = 0
        self._lock = threading.Lock()
        self._failure = threading.Event()
        self._stream_ended = threading.Event()
        self._closing = threading.Event()

    def _bounded(self, action: Callable[[], _T], deadline: float) -> _T:
        result: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

        def invoke() -> None:
            try:
                result.put((True, action()))
            except BaseException as exc:
                result.put((False, exc))

        threading.Thread(target=invoke, daemon=True).start()
        try:
            success, value = result.get(
                timeout=max(0.001, deadline - time.monotonic())
            )
        except queue.Empty:
            raise TimeoutError(
                "Sandbox operation exceeded controller deadline"
            ) from None
        if not success:
            assert isinstance(value, BaseException)
            raise value
        from typing import cast

        return cast(_T, value)

    def _drain(self) -> None:
        assert self._process is not None
        try:
            for text in self._process.stdout():
                if self._closing.is_set():
                    break
                if len(text) > _FRAME_LINE_LIMIT:
                    self._failure.set()
                    break
                chunk = base64.b64decode(text.rstrip("\n"), validate=True)
                if not chunk or len(chunk) > _FRAME_BYTES:
                    self._failure.set()
                    break
                with self._lock:
                    if self._queued_bytes + len(chunk) > MAX_OUTPUT + 256:
                        self._failure.set()
                        break
                    self._queued_bytes += len(chunk)
                try:
                    self._output.put_nowait(chunk)
                except queue.Full:
                    self._failure.set()
                    break
        except Exception:
            self._failure.set()
        finally:
            self._stream_ended.set()

    def _run(self, command: list[str], deadline: float) -> None:
        def run() -> None:
            process = self.session.exec(command)
            code = process.wait(
                timeout=max(0.001, deadline - time.monotonic())
            )
            if code != 0:
                raise RuntimeError(f"Sandbox control command exited {code}")

        self._bounded(run, deadline)

    def start(self) -> None:
        """Create the FIFO and initialize the persistent shell.

        Raises:
            RuntimeError: Startup fails or this shell was already used.
            BaseException: Startup failures propagate after closing handles.
        """
        if self._started or self.stopped:
            raise RuntimeError("Shell instances cannot be restarted")
        self._started = True
        self._deadline = time.monotonic() + self.episode_timeout
        deadline = min(self._deadline, time.monotonic() + self.command_timeout)
        try:
            self._run(
                [
                    "bash",
                    "-c",
                    f"mkdir -m 700 {self._control}; "
                    f"mkfifo {self._control}/input",
                ],
                deadline,
            )

            def launch() -> SandboxProcess:
                process = self.session.exec(
                    [
                        "bash",
                        "-c",
                        f"exec 3<>{self._control}/input; "
                        "bash --noprofile --norc <&3 2>&1 | "
                        "python3 -u -c " + shlex.quote(_FRAMER),
                    ]
                )
                return process

            self._process = self._bounded(launch, deadline)
            threading.Thread(target=self._drain, daemon=True).start()
            ok, output = self.execute(
                "export HOME=/home/user; cd /home/user; set -o pipefail"
            )
            if not ok:
                raise RuntimeError("Shell initialization failed: " + output)
        except BaseException:
            self.close()
            raise

    def execute(self, command: str) -> tuple[bool, str]:
        """Execute one command while preserving Bash state.

        Args:
            command: Shell command to evaluate.

        Returns:
            Success flag and bounded output. Transport failure, timeout or
            output overflow stops this shell; the caller must destroy its
            sandbox before grading. Ordinary exceptions become failed results.
        """  # noqa: DOC501,DOC503
        if self.stopped or self._process is None:
            return False, "Terminal is stopped"
        deadline = min(self._deadline, time.monotonic() + self.command_timeout)
        if deadline <= time.monotonic():
            self.close()
            return False, "Episode deadline exceeded; terminal stopped"
        if len(command.encode()) > MAX_OUTPUT:
            self.close()
            return False, "Command size limit exceeded; terminal stopped"
        token = "ENDLESS_" + uuid.uuid4().hex
        marker = re.compile(rb"\x1e" + token.encode() + rb":([0-9]+)\x1f\n")
        script = (
            "eval "
            + shlex.quote(command)
            + "\nbuiltin printf '\\036"
            + token
            + ':%s\\037\\n\' "$?"\n'
        )
        output = bytearray()
        try:
            with tempfile.TemporaryDirectory(
                prefix="endless-fifo-"
            ) as directory:
                path = Path(directory) / "command"
                path.write_text(script)
                remote = self._control + "/" + token
                self._bounded(
                    lambda: self.session.upload_file(str(path), remote),
                    deadline,
                )
            seconds = max(0.001, deadline - time.monotonic())
            self._run(
                [
                    "timeout",
                    "--kill-after=1",
                    str(seconds),
                    "bash",
                    "-c",
                    f"cat {remote} > {self._control}/input; rm -f {remote}",
                ],
                deadline,
            )
            while time.monotonic() < deadline:
                if self._failure.is_set():
                    raise RuntimeError(
                        "Shell output overflow or stream failure"
                    )
                try:
                    chunk = self._output.get(
                        timeout=min(
                            0.05, max(0.001, deadline - time.monotonic())
                        )
                    )
                except queue.Empty:
                    if self._stream_ended.is_set():
                        raise RuntimeError("Shell output stream ended")
                    continue
                with self._lock:
                    self._queued_bytes -= len(chunk)
                output.extend(chunk)
                match = marker.search(output)
                if match and match.start() <= MAX_OUTPUT:
                    return int(match[1]) == 0, output[: match.start()].decode(
                        errors="replace"
                    )
                if len(output) > MAX_OUTPUT:
                    raise RuntimeError("Shell output limit exceeded")
            raise TimeoutError("Command or episode deadline exceeded")
        except Exception as exc:
            self.close()
            return False, output[:MAX_OUTPUT].decode(
                errors="replace"
            ) + f"\n{exc}; terminal stopped"

    def close(self) -> None:
        """Stop accepting commands and consuming output.

        The caller must destroy the sandbox to stop remote processes and unblock
        stream readers. Per-process kill is unsupported on some backends and
        may destroy the entire session on others.
        """
        self.stopped = True
        self._closing.set()
