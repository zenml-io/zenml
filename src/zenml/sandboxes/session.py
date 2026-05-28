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
"""Session abstraction.

Sessions are created by ``BaseSandbox.create_session()``, accept many
``exec`` calls, and are closed via ``close()`` (releases the local
handle, sandbox keeps running on the provider until its TTL) or
``destroy()`` (terminates immediately).

Sandbox-log forwarding writes **only** the actual sandbox execution
surface to a dedicated ``sandbox:<id>`` log source:

* the command line on each ``exec`` call (``$ python -c ...``)
* the sandbox process's stdout lines (level INFO)
* the sandbox process's stderr lines (level WARNING)

Routing is direct: each line is emitted straight to a per-session
``BaseLogStoreOrigin`` via ``log_store.emit(...)``. The base class
does NOT push a ``LoggingContext`` onto the step's logging stack, so
incidental ``logger.info(...)`` calls in the step process (e.g. from
``zenml`` internals) are NOT captured under the sandbox source. They
stay in the regular step log where they belong.

Step metadata (sandbox session id, flavor, optional dashboard URL) is
published once on ``__enter__`` via ``_on_enter()`` and keyed by the
session id so multiple sessions in one step don't overwrite each
other.
"""

import logging
import shlex
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
    from zenml.log_stores.base_log_store import (
        BaseLogStore,
        BaseLogStoreOrigin,
    )
    from zenml.models import LogsResponse
    from zenml.sandboxes.base import BaseSandbox


logger = get_logger(__name__)


class SandboxSession(ABC):
    """A live, bounded interaction with a single isolated execution environment.

    Subclasses must implement ``exec`` and ``close``. The framework does
    **not** auto-close Sessions on step exit — see ADR 0002 for why this
    matters for the subagent-attach flow.

    Lifecycle invariants the base class owns:

    * ``self.id`` is set in ``__init__`` and stable for the Session's lifetime.
    * ``__enter__`` publishes step metadata (session id, flavor, optional
      dashboard URL via ``_dashboard_url()``) keyed by session id.
    * ``__exit__`` calls ``close()``; subclasses release the sandbox log
      origin by calling ``_close_log_origin()`` from their ``close()`` impl.
    * The sandbox log origin is created lazily on first ``_emit_sandbox()``
      (or first ``_log_command`` / ``_wrap_stream`` call) so sessions that
      never produce output don't create empty log artifacts.
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
            parent: The owning ``BaseSandbox`` component.
        """
        self.id = id
        self._parent = parent
        self._log_store: Optional["BaseLogStore"] = None
        self._log_origin: Optional["BaseLogStoreOrigin"] = None
        self._log_response: Optional["LogsResponse"] = None
        # Latched off when origin setup fails so we don't keep retrying
        # every emit — keeps the failure noisy once, then quiet.
        self._log_forwarding_disabled = False

    @abstractmethod
    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Starts a command in the Session and returns a handle.

        ``command`` accepts a list (no shell escaping needed) or a string
        (run via the Session's default shell — flavors should pick a sane
        shell or escape via ``shlex.join`` internally).

        Flavor implementations should call ``self._log_command(command)``
        before launching so the sandbox log captures the command line.

        Raises ``SandboxExecError`` synchronously if the command fails to
        launch (e.g. binary not found, image broken). Runtime failures flow
        through the returned ``SandboxProcess``.
        """

    async def aexec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Async sibling of ``exec``. Optional; default raises NotImplementedError."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support async exec. "
            "Use exec() instead."
        )

    def snapshot(self) -> BaseSandboxSnapshot:
        """Captures Session state. Returns a serializable handle for restore.

        Optional; default raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support snapshots."
        )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file into the Session's filesystem.

        Optional; default raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support file uploads."
        )

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the Session's filesystem to local storage.

        Optional; default raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support file downloads."
        )

    @abstractmethod
    def close(self) -> None:
        """Releases this local handle. Cheap; safe to call multiple times.

        Subclasses must call ``self._close_log_origin()`` from their
        override to deregister the sandbox log origin (which flushes
        the source to the log store).

        The sandbox keeps running on the provider until its TTL expires or
        ``destroy()`` is called. Implicitly invoked by ``__exit__``.
        """

    def destroy(self) -> None:
        """Terminates the sandbox on the provider.

        After this, the session id becomes invalid; ``attach()`` will fail.
        Optional; default raises NotImplementedError. Flavors that support
        only forced cleanup (e.g. via TTL) should leave this unimplemented.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support explicit destroy. "
            "Rely on close() and the provider's session TTL."
        )

    # ----- lifecycle hooks: implemented here, overridable by flavors ------

    def _dashboard_url(self) -> Optional[str]:
        """Returns a URL to the provider's UI for this Session, if any.

        Default: ``None`` — no link is published. Flavors override to
        return a clickable URL that ZenML logs as step metadata typed
        ``Uri`` so the dashboard renders it as a link.

        Returns:
            URL string or ``None``.
        """
        return None

    def _on_enter(self) -> None:
        """Publishes generic sandbox step metadata.

        Hook called from ``__enter__``. Records ``sandbox.<id>.flavor``
        and (when ``_dashboard_url()`` returns a non-None value)
        ``sandbox.<id>.dashboard_url`` (typed ``Uri``) on the active
        step. The session id is embedded in the key so steps that open
        multiple sandbox sessions don't overwrite each other's metadata.

        No-ops gracefully when called outside a step context (e.g.
        ad-hoc usage from a script) — ``log_metadata`` raises
        ``ValueError`` which we log at DEBUG. Any other failure
        (network, serialization) is logged at WARNING so it's debuggable
        without breaking sandbox usage.
        """
        from zenml.metadata.metadata_types import MetadataType, Uri
        from zenml.utils.metadata_utils import log_metadata

        prefix = f"sandbox.{self.id}"
        metadata: Dict[str, MetadataType] = {
            f"{prefix}.flavor": self._parent.flavor,
        }
        url = self._dashboard_url()
        if url:
            metadata[f"{prefix}.dashboard_url"] = Uri(url)
        try:
            log_metadata(metadata=metadata)
        except ValueError as e:
            # log_metadata raises ValueError when invoked outside a step
            # context (e.g. ad-hoc Client().active_stack.sandbox usage).
            # That's expected here; anything else escalates below.
            logger.debug(
                "Skipping sandbox step metadata (no active step): %s", e
            )
        except Exception as e:
            # Real failure (network error, serialization bug, etc.). Don't
            # break sandbox usage, but make it visible so it's debuggable.
            logger.warning("Failed to publish sandbox step metadata: %s", e)

    # ----- sandbox log emission ------------------------------------------

    def _ensure_log_origin(self) -> Optional["BaseLogStoreOrigin"]:
        """Lazily creates the per-session log origin on first emit.

        The origin is bound to a dedicated ``sandbox:<id>`` source — a
        side-channel into the active step's log store that does NOT
        share the active ``LoggingContext`` stack, so step-side
        logger calls don't leak into the sandbox source.

        Returns:
            The origin to emit to, or ``None`` when setup has failed
            for this session (latched after first failure).
        """
        if self._log_forwarding_disabled:
            return None
        if self._log_origin is not None:
            return self._log_origin

        try:
            from zenml.client import Client
            from zenml.steps.step_context import StepContext
            from zenml.utils.logging_utils import (
                generate_logs_request,
                get_run_log_metadata,
                get_step_log_metadata,
            )

            log_store = Client().active_stack.log_store
            logs_request = generate_logs_request(source=f"sandbox:{self.id}")
            metadata: Dict[str, Any] = {}
            ctx = StepContext.get()
            if ctx is not None:
                logs_request.step_run_id = ctx.step_run.id
                metadata.update(get_step_log_metadata(step_run=ctx.step_run))
                metadata.update(
                    get_run_log_metadata(pipeline_run=ctx.pipeline_run)
                )
            log_response = Client().zen_store.create_logs(logs_request)
            origin = log_store.register_origin(
                name=f"sandbox:{self.id}",
                log_model=log_response,
                metadata=metadata,
            )
        except Exception as e:
            logger.debug(
                "Sandbox log forwarding disabled for session %s: %s",
                self.id,
                e,
            )
            self._log_forwarding_disabled = True
            return None

        self._log_store = log_store
        self._log_response = log_response
        self._log_origin = origin
        return origin

    def _emit_sandbox(
        self, message: str, *, level: int = logging.INFO
    ) -> None:
        """Writes a single line to the sandbox log source.

        Bypasses the global ``LoggingContext`` stack so this only
        records sandbox-execution events, never incidental step-side
        Python logger calls.

        Args:
            message: The text to emit (newlines should be stripped
                before calling).
            level: The log level (INFO for stdout / command,
                WARNING for stderr).
        """
        origin = self._ensure_log_origin()
        if origin is None or self._log_store is None:
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
        try:
            self._log_store.emit(origin=origin, record=record)
        except Exception:
            logger.debug(
                "Failed to emit sandbox log line for %s",
                self.id,
                exc_info=True,
            )

    def _log_command(self, command: Union[str, List[str]]) -> None:
        """Records the command about to be executed.

        Flavor ``exec`` impls call this immediately before launching so
        the sandbox log opens with a shell-style ``$ <command>`` marker.

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

        Emits ``✓ exit 0 in 1.3s`` (or ``✗ exit 1 in 0.2s`` for non-zero
        codes) as a trailing marker so the sandbox log reads like a
        shell session: command → output → result.

        Levels: success at INFO, failure at WARNING — the dashboard
        renders the failure rows with their own treatment.

        Args:
            exit_code: The exit code reported by the sandbox.
            started_at: Wall-clock start time captured by the flavor
                when exec'ing. ``None`` skips the duration suffix.
        """
        glyph = "✓" if exit_code == 0 else "✗"
        if started_at is not None:
            elapsed = time.time() - started_at
            message = f"{glyph} exit {exit_code} in {elapsed:.1f}s"
        else:
            message = f"{glyph} exit {exit_code}"
        level = logging.INFO if exit_code == 0 else logging.WARNING
        self._emit_sandbox(message, level=level)

    def _wrap_stream(
        self, lines: Iterator[str], *, stream: str = "stdout"
    ) -> Iterator[str]:
        """Yields each line after emitting it to the sandbox log source.

        Flavor process impls wrap their raw stdout/stderr iterators in
        this so the sandbox log captures live output as the sandbox
        process emits it. When forwarding is disabled, lines pass
        through unchanged.

        Args:
            lines: Source line iterator from the flavor's process.
            stream: ``"stdout"`` → INFO, ``"stderr"`` → WARNING.

        Yields:
            Each line from the source iterator, unchanged.
        """
        if self._log_forwarding_disabled:
            yield from lines
            return
        level = logging.INFO if stream == "stdout" else logging.WARNING
        for line in lines:
            self._emit_sandbox(line.rstrip("\n"), level=level)
            yield line

    def _close_log_origin(self) -> None:
        """Deregisters the sandbox log origin (flushes the source).

        Idempotent — safe to call multiple times. Subclasses call this
        from their ``close()`` so the per-session log is finalized and
        readable from the dashboard.
        """
        if self._log_origin is not None and self._log_store is not None:
            try:
                self._log_store.deregister_origin(self._log_origin)
            except Exception:
                logger.debug(
                    "Failed to deregister sandbox log origin for %s",
                    self.id,
                    exc_info=True,
                )
            finally:
                self._log_origin = None
                self._log_store = None
                self._log_response = None

    def __enter__(self) -> "SandboxSession":
        """Publishes step metadata.

        The sandbox log origin is NOT created here -- it's lazily
        created on the first ``exec`` call so sessions that never run
        a command don't leave empty log artifacts behind.

        Returns:
            This session.
        """
        self._on_enter()
        return self

    def __exit__(self, *args: Any) -> None:
        """Releases the local handle on context-manager exit.

        Args:
            *args: Exception info; ignored — ``close()`` is best-effort.
        """
        self.close()
