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
"""Sandbox session abstraction."""

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
from zenml.sandboxes.snapshot import BaseSandboxSnapshot

if TYPE_CHECKING:
    from zenml.sandboxes.base import BaseSandbox
    from zenml.utils.logging_utils import LoggingContext


logger = get_logger(__name__)


class SandboxSession(ABC):
    """A live, bounded interaction with a single isolated execution environment.

    Subclasses must implement `exec` and `close`. Lifecycle invariants
    the base class owns:

    - `self.id` is set in `__init__` and stable for the Session's
      lifetime.
    - `__enter__` publishes step metadata (session id, flavor,
      optional dashboard URL via `_dashboard_url()`) keyed by session
      id so multiple sessions in one step don't overwrite each other.
    - `__exit__` calls `close()` then `_close_log_ctx()`, so the
      per-session log source is always flushed even when a subclass
      `close()` raises or forgets the explicit call.
    - The sandbox log origin is created lazily on the first
      `_emit_sandbox()` call so sessions that never produce output
      don't create empty log artifacts.
    """

    def __init__(
        self,
        *,
        id: str,
        parent: "BaseSandbox",
    ) -> None:
        """Initializes the session lifecycle state.

        Args:
            id: Stable session identifier (flavor decides the format).
            parent: The owning `BaseSandbox` component.
        """
        self.id = id
        self._parent = parent
        self._log_ctx: Optional["LoggingContext"] = None
        # Latched off when log-context setup fails so we don't keep
        # retrying every emit.
        self._log_forwarding_disabled = False
        self._log_setup_lock = threading.Lock()

    @abstractmethod
    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Starts a command in the Session and returns a handle.

        `command` accepts a list (no shell escaping needed) or a
        string (run via the Session's default shell). Flavor
        implementations should call `self._log_command(command)`
        before launching so the sandbox log captures the command
        line. Synchronous launch errors raise `SandboxExecError`.
        Runtime failures flow through the returned `SandboxProcess`.
        """

    async def aexec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Async sibling of `exec`. Default raises NotImplementedError.

        Args:
            command: Command argv or shell string.
            cwd: Optional working directory override.
            env: Optional per-exec env vars.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support async exec. "
            "Use exec() instead."
        )

    def snapshot(self) -> BaseSandboxSnapshot:
        """Captures Session state, returning a serializable handle for restore.

        Default raises NotImplementedError.

        Returns:
            A `BaseSandboxSnapshot` handle.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support snapshots."
        )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file into the Session's filesystem.

        Default raises NotImplementedError.

        Args:
            local_path: Source path on the caller's filesystem.
            remote_path: Destination path inside the sandbox.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support file uploads."
        )

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the Session's filesystem to local storage.

        Default raises NotImplementedError.

        Args:
            remote_path: Source path inside the sandbox.
            local_path: Destination path on the caller's filesystem.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support file downloads."
        )

    @abstractmethod
    def close(self) -> None:
        """Releases this local handle. Safe to call multiple times.

        The base `__exit__` calls `_close_log_ctx()` after `close()`
        so subclasses are not required to do it themselves. Calling
        `_close_log_ctx()` from the subclass override is idempotent
        and safe if early flushing is desired.

        The sandbox keeps running on the provider until its TTL
        expires or `destroy()` is called.
        """

    def destroy(self) -> None:
        """Terminates the sandbox on the provider.

        After this, the session id becomes invalid and `attach()`
        will fail. Default raises NotImplementedError. Flavors that
        support only TTL-based cleanup should leave this unimplemented.

        Raises:
            NotImplementedError: Default. Flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support explicit destroy. "
            "Rely on close() and the provider's session TTL."
        )

    def _dashboard_url(self) -> Optional[str]:
        """Returns a URL to the provider's UI for this Session, if any.

        Returns:
            URL string or `None`. Default `None`. Flavors override to
            return a clickable URL that ZenML logs as step metadata
            typed `Uri` so the dashboard renders it as a link.
        """
        return None

    def _on_enter(self) -> None:
        """Publishes generic sandbox step metadata.

        Hook called from `__enter__`. Records `sandbox.<id>.flavor`
        and (when `_dashboard_url()` returns a non-None value)
        `sandbox.<id>.dashboard_url` (typed `Uri`) on the active
        step. The session id is embedded in the key so multiple
        sandbox sessions in one step don't overwrite each other's
        metadata.

        No-ops gracefully when called outside a step context (e.g.
        ad-hoc usage from a script), `log_metadata` raises
        `ValueError` which we log at DEBUG. Any other failure
        (network, serialization) is logged at WARNING.
        """
        from zenml.metadata.metadata_types import MetadataType, Uri
        from zenml.utils.metadata_utils import log_metadata

        prefix = f"sandbox.{self.id}"
        metadata: Dict[str, MetadataType] = {
            f"{prefix}.flavor": self._parent.flavor,
        }
        if url := self._dashboard_url():
            metadata[f"{prefix}.dashboard_url"] = Uri(url)
        try:
            log_metadata(metadata=metadata)
        except ValueError as e:
            # log_metadata raises ValueError when invoked outside a step
            # context (e.g. ad-hoc Client().active_stack.sandbox usage).
            logger.debug(
                "Skipping sandbox step metadata (no active step): %s", e
            )
        except Exception as e:
            logger.warning("Failed to publish sandbox step metadata: %s", e)

    def _ensure_log_ctx(self) -> Optional["LoggingContext"]:
        """Lazily sets up the per-session `LoggingContext` on first emit.

        Built via `setup_logging_context` (so the LogsResponse is
        created and linked to the active step the same way as every
        other ZenML log source), but registered via `ctx.begin()`,
        not a `with` block, so this source does NOT join the thread's
        active-context stack. Step-side `logger.info(...)` calls
        stay in the regular step source; sandbox commands and
        stdout/stderr land in `sandbox:<id>`.

        Returns:
            The bound logging context, or `None` when setup has
            failed for this session (latched after first failure).
        """
        if self._log_forwarding_disabled:
            return None
        if self._log_ctx is not None:
            return self._log_ctx

        with self._log_setup_lock:
            if self._log_forwarding_disabled:
                return None
            if self._log_ctx is not None:
                return self._log_ctx

            try:
                from zenml.steps.step_context import StepContext
                from zenml.utils.logging_utils import setup_logging_context

                step_ctx = StepContext.get()
                ctx = setup_logging_context(
                    source=f"sandbox:{self.id}",
                    step_run=step_ctx.step_run if step_ctx else None,
                    pipeline_run=step_ctx.pipeline_run if step_ctx else None,
                )
                ctx.begin()
            except Exception as e:
                logger.debug(
                    "Sandbox log forwarding disabled for session %s: %s",
                    self.id,
                    e,
                )
                self._log_forwarding_disabled = True
                return None

            self._log_ctx = ctx
            return ctx

    def _emit_sandbox(
        self, message: str, *, level: int = logging.INFO
    ) -> None:
        """Writes a single line to the sandbox log source.

        Routes through `LoggingContext.emit_to` so the
        `sandbox:<id>` source captures only sandbox-execution events,
        not incidental step-side Python logger calls.

        Args:
            message: The text to emit (newlines should be stripped
                before calling).
            level: The log level for the entry.
        """
        ctx = self._ensure_log_ctx()
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
        ctx.emit_to(record)

    def _log_command(self, command: Union[str, List[str]]) -> None:
        """Records the command about to be executed.

        Flavor `exec` impls call this immediately before launching so
        the sandbox log opens with a shell-style `$ <command>` marker.

        Note: persists the full argv to the sandbox log source. Pass
        secrets via env vars, not on the command line.

        Args:
            command: The command argv or shell string.
        """
        if isinstance(command, list):
            display = " ".join(shlex.quote(c) for c in command)
        else:
            display = command
        self._emit_sandbox(f"$ {display}", level=logging.INFO)

    def _log_exec_result(
        self,
        *,
        exit_code: int,
        started_at: Optional[float] = None,
    ) -> None:
        """Records the result of an exec after collect() drains.

        Emits `OK exit 0 in 1.3s` (or `FAIL exit 1 in 0.2s` for
        non-zero codes) as a trailing marker so the sandbox log reads
        like a shell session: command, output, result.

        Levels: success at INFO, failure at WARNING. The dashboard
        renders the failure rows with their own treatment.

        Args:
            exit_code: The exit code reported by the sandbox.
            started_at: Wall-clock start time captured by the flavor
                when exec'ing. `None` skips the duration suffix.
        """
        tag = "OK" if exit_code == 0 else "FAIL"
        if started_at is not None:
            elapsed = time.time() - started_at
            message = f"{tag} exit {exit_code} in {elapsed:.1f}s"
        else:
            message = f"{tag} exit {exit_code}"
        level = logging.INFO if exit_code == 0 else logging.WARNING
        self._emit_sandbox(message, level=level)

    def _wrap_stream(
        self, lines: Iterator[str], *, stream: str = "stdout"
    ) -> Iterator[str]:
        """Yields each line after emitting it to the sandbox log source.

        Flavor process impls wrap their raw stdout/stderr iterators
        in this so the sandbox log captures live output as the
        sandbox process emits it. When forwarding is disabled, lines
        pass through unchanged. Both stdout and stderr emit at INFO,
        since sandbox stderr is just diagnostic output, not an
        application-level warning.

        Args:
            lines: Source line iterator from the flavor's process.
            stream: `"stdout"` or `"stderr"`. Currently both emit at
                INFO; kept on the signature so callers can record
                stream attribution downstream.

        Yields:
            Each line from the source iterator, unchanged.
        """
        del stream
        if self._log_forwarding_disabled:
            yield from lines
            return
        for line in lines:
            self._emit_sandbox(line.rstrip("\n"), level=logging.INFO)
            yield line

    def _close_log_ctx(self) -> None:
        """Deregisters the sandbox log origin (flushes the source).

        Idempotent. The base `__exit__` calls this after `close()`
        so subclasses do not need to call it explicitly.
        """
        if self._log_ctx is not None:
            try:
                self._log_ctx.end()
            except Exception:
                logger.debug(
                    "Failed to close sandbox log context for %s",
                    self.id,
                    exc_info=True,
                )
            finally:
                self._log_ctx = None

    def __enter__(self) -> "SandboxSession":
        """Publishes step metadata.

        The sandbox log origin is NOT created here. It's lazily
        created on the first `exec` call so sessions that never run
        a command don't leave empty log artifacts behind.

        Returns:
            This session.
        """
        self._on_enter()
        return self

    def __exit__(self, *args: Any) -> None:
        """Releases the local handle and deregisters the sandbox log origin.

        Guarantees `_close_log_ctx()` runs even if the subclass
        `close()` raises or forgets to call it. `_close_log_ctx()`
        is idempotent so calling it from the subclass `close()` and
        again here is safe.

        Args:
            *args: Exception info, ignored. `close()` is permitted
                to raise but the log cleanup still runs.
        """
        try:
            self.close()
        finally:
            self._close_log_ctx()
