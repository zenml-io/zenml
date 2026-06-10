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
"""Sandbox session."""

import logging
import shlex
import threading
import time
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)

from zenml.logger import get_logger
from zenml.sandboxes.process import SandboxProcess
from zenml.sandboxes.snapshot import SandboxSnapshot

if TYPE_CHECKING:
    from zenml.sandboxes.base import BaseSandbox
    from zenml.utils.logging_utils import LoggingContext


logger = get_logger(__name__)


class SandboxSessionClosedError(RuntimeError):
    """Raised when a closed sandbox session is used."""


class SandboxSession(ABC):
    """Sandbox session."""

    def __init__(
        self,
        *,
        id: str,
        parent: "BaseSandbox",
    ) -> None:
        """Initialize the sandbox session.

        Args:
            id: Session identifier.
            parent: The sandbox component that created this session.
        """
        self.id = id
        self._parent = parent
        self._closed = False
        self._logging_context: Optional["LoggingContext"] = None
        self._logging_disabled = False
        self._logging_lock = threading.Lock()
        self._publish_sandbox_metadata()

    @property
    def closed(self) -> bool:
        """Whether this session handle has been closed.

        Returns:
            ``True`` once `close()` or `destroy()` has been called.
        """
        return self._closed

    def _ensure_open(self) -> None:
        """Reject use of a closed session handle.

        Raises:
            SandboxSessionClosedError: If the session has been closed.
        """
        if self._closed:
            raise SandboxSessionClosedError(
                f"Sandbox session `{self.id}` has been closed. Create a "
                "new session (or re-attach to the sandbox) to keep "
                "interacting with it."
            )

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Execute a command in the sandbox session.

        Args:
            command: The command to execute.
            cwd: Optional working directory override.
            env: Optional environment variables to set in the environment
                executing the command.

        Returns:
            Process handle.
        """
        self._ensure_open()
        return self._exec(command, cwd=cwd, env=env)

    @abstractmethod
    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Flavor-specific command execution, called by `exec()`.

        Args:
            command: The command to execute.
            cwd: Optional working directory override.
            env: Optional environment variables to set in the environment
                executing the command.

        Returns:
            Process handle.
        """

    async def aexec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Async execute a command in the sandbox session.

        Args:
            command: The command to execute.
            cwd: Optional working directory override.
            env: Optional environment variables to set in the environment
                executing the command.

        Raises:
            NotImplementedError: If the sandbox does not support async exec.

        Returns:
            Process handle.
        """
        self._ensure_open()
        raise NotImplementedError(
            f"{type(self).__name__} does not support async execution."
        )

    def create_snapshot(self) -> SandboxSnapshot:
        """Create a snapshot of the sandbox session.

        Returns:
            A sandbox snapshot.
        """
        self._ensure_open()
        return self._create_snapshot()

    def _create_snapshot(self) -> SandboxSnapshot:
        """Flavor-specific snapshot creation, called by `create_snapshot()`.

        Raises:
            NotImplementedError: If the sandbox does not support creating
                snapshots.

        Returns:
            A sandbox snapshot.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support creating snapshots."
        )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to the sandbox session.

        Args:
            local_path: Source path on the caller's filesystem.
            remote_path: Destination path in the sandbox.
        """
        self._ensure_open()
        self._upload_file(local_path, remote_path)

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Flavor-specific file upload, called by `upload_file()`.

        Args:
            local_path: Source path on the caller's filesystem.
            remote_path: Destination path in the sandbox.

        Raises:
            NotImplementedError: If the sandbox does not support file uploads.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support file uploads."
        )

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the sandbox to the local filesystem.

        Args:
            remote_path: Source path in the sandbox.
            local_path: Destination path on the caller's filesystem.
        """
        self._ensure_open()
        self._download_file(remote_path, local_path)

    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Flavor-specific file download, called by `download_file()`.

        Args:
            remote_path: Source path in the sandbox.
            local_path: Destination path on the caller's filesystem.

        Raises:
            NotImplementedError: If the sandbox does not support file downloads.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support file downloads."
        )

    def close(self) -> None:
        """Close the sandbox session handle. Terminal and idempotent.

        After closing, the session handle rejects further use (`exec`,
        snapshots, file transfer) — re-attach to the sandbox for a fresh
        handle. For remote sandboxes, closing does not terminate the
        sandbox on the provider: it keeps running until its TTL expires
        or `destroy()` is called.
        """
        if self._closed:
            return
        self._closed = True
        try:
            self._close()
        finally:
            self._close_logging_context()

    @abstractmethod
    def _close(self) -> None:
        """Release flavor-specific session resources.

        Called by `close()`, which owns the logging-context cleanup —
        implementations must not need to (and cannot forget to) close it
        themselves.
        """

    def destroy(self) -> None:
        """Destroy the sandbox session. Terminal like `close()`.

        Terminates the sandbox on the provider and then closes this
        handle, so after a successful call it is no longer possible to
        attach to the session. Flavor failures (including
        `NotImplementedError` from flavors without destroy support)
        propagate and leave the handle open for retry, because the
        flavor hook runs before `close()`. Callable on an
        already-closed handle: `close()` is idempotent.
        """
        self._destroy()
        self.close()

    def _destroy(self) -> None:
        """Flavor-specific session destruction, called by `destroy()`.

        Raises:
            NotImplementedError: If the sandbox does not support destroying
                sessions.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support destroying sessions."
        )

    def _get_dashboard_url(self) -> Optional[str]:
        """Get a URL to the provider's UI for this session, if any.

        Returns:
            The dashboard URL for this session.
        """
        return None

    def _publish_sandbox_metadata(self) -> None:
        """Publish sandbox metadata for the active step."""
        from zenml.metadata.metadata_types import MetadataType, Uri
        from zenml.utils.metadata_utils import log_metadata

        prefix = f"sandbox.{self.id}"
        metadata: Dict[str, MetadataType] = {
            f"{prefix}.flavor": self._parent.flavor,
        }

        # Called during construction, so a subclass dashboard hook may
        # not have its state yet. Guard it so a failure can't break
        # session creation. Flavors that build the URL from subclass
        # state should set it before super().__init__().
        try:
            url = self._get_dashboard_url()
        except Exception:
            url = None

        if url:
            metadata[f"{prefix}.dashboard_url"] = Uri(url)

        try:
            log_metadata(metadata=metadata)
        except ValueError as e:
            logger.debug(
                "Skipping sandbox step metadata (no active step): %s", e
            )
        except Exception as e:
            logger.warning("Failed to publish sandbox step metadata: %s", e)

    def _get_logging_context(self) -> Optional["LoggingContext"]:
        """Get the logging context for the sandbox session.

        Returns:
            The logging context or None if logging is disabled.
        """
        # Check without locking first for speed.
        if self._logging_disabled:
            return None

        if self._logging_context is not None:
            return self._logging_context

        with self._logging_lock:
            if self._logging_disabled:
                return None

            if self._logging_context is not None:
                return self._logging_context

            try:
                from zenml.steps.step_context import StepContext
                from zenml.utils.logging_utils import setup_logging_context

                step_ctx = StepContext.get()
                if step_ctx is None:
                    # No active step means there is nothing to attach logs
                    # to. Latch off instead of creating an orphan logs
                    # record untethered to any run.
                    self._logging_disabled = True
                    return None

                logging_context = setup_logging_context(
                    source=f"sandbox:{self.id}",
                    step_run=step_ctx.step_run,
                    pipeline_run=step_ctx.pipeline_run,
                )
                logging_context.begin()
            except Exception as e:
                logger.debug(
                    "Sandbox log forwarding disabled for session %s: %s",
                    self.id,
                    e,
                )
                self._logging_disabled = True
                return None

            self._logging_context = logging_context
            return logging_context

    def _emit_log(self, message: str, *, level: int = logging.INFO) -> None:
        """Emit a single line to the sandbox log source.

        Args:
            message: The message to emit.
            level: The log level.
        """
        ctx = self._get_logging_context()
        if ctx is None:
            return

        record = logging.LogRecord(
            name=f"sandbox.{self.id}",
            level=level,
            pathname="",
            lineno=0,
            msg="%s",
            args=(message,),
            exc_info=None,
        )
        ctx.emit(record)

    def _log_command(self, command: Union[str, List[str]]) -> None:
        """Log the command about to be executed.

        Args:
            command: The command.
        """
        if isinstance(command, list):
            display = " ".join(shlex.quote(c) for c in command)
        else:
            display = command

        self._emit_log(f"$ {display}", level=logging.INFO)

    def _log_exec_result(self, *, exit_code: int, started_at: float) -> None:
        """Log the result of an exec call.

        Args:
            exit_code: The exit code.
            started_at: The wall-clock start time.
        """
        tag = "OK" if exit_code == 0 else "FAIL"
        elapsed = time.time() - started_at
        message = f"{tag} exit code {exit_code} in {elapsed:.1f}s"
        level = logging.INFO if exit_code == 0 else logging.ERROR
        self._emit_log(message, level=level)

    def _wrap_stream(
        self, lines: Iterator[str], *, log_level: int = logging.INFO
    ) -> Iterator[str]:
        """Wrap the stream to emit each line to the sandbox log source.

        Args:
            lines: The lines to wrap.
            log_level: The log level.

        Yields:
            Each line from the source iterator.
        """
        if self._logging_disabled:
            yield from lines
            return

        for line in lines:
            self._emit_log(line.rstrip("\n"), level=log_level)
            yield line

    def _close_logging_context(self) -> None:
        """Close the logging context for the sandbox session.

        Closing is terminal: the context is created lazily on first emit,
        so without disabling further creation here, any emit after close
        (e.g. draining a leftover stream) would silently resurrect a new
        context that nothing ever closes.
        """
        with self._logging_lock:
            self._logging_disabled = True
            if self._logging_context is not None:
                try:
                    self._logging_context.end()
                except Exception:
                    logger.debug(
                        "Failed to close logging context for sandbox "
                        "session `%s`.",
                        self.id,
                        exc_info=True,
                    )
                finally:
                    self._logging_context = None

    def __enter__(self) -> "SandboxSession":
        """Enter the sandbox session context manager.

        Returns:
            The sandbox session.
        """
        return self

    def __exit__(self, *_: Any) -> None:
        """Close the session."""
        self.close()
