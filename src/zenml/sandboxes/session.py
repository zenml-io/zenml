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

Lifecycle plumbing — opening a per-session ZenML logging context so
sandbox stdout/stderr surfaces as a dedicated ``sandbox:<id>`` source
in the step log stream, plus publishing the session id / flavor /
dashboard URL as step metadata — lives on this base class so every
flavor inherits it. Flavors only need to implement the transport
(``exec``/``close``) and optionally override ``_dashboard_url()``.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from zenml.logger import get_logger
from zenml.sandboxes.process import SandboxProcess
from zenml.sandboxes.snapshot import BaseSandboxSnapshot

if TYPE_CHECKING:
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
      dashboard URL via ``_dashboard_url()``) and opens the log-forwarding
      ``LoggingContext`` exactly once when ``forward_logs`` is True.
    * ``__exit__`` calls ``close()``; subclasses release the log context by
      calling ``_close_log_ctx()`` from their ``close()`` impl.
    * Both step-metadata and log-forwarding only fire inside a ``with``
      block. ``s = sandbox.create_session(); s.close()`` skips them.
    """

    def __init__(
        self,
        *,
        id: str,
        parent: "BaseSandbox",
        forward_logs: bool = False,
    ) -> None:
        """Initializes the session lifecycle state.

        Args:
            id: Stable session identifier (flavor decides the format).
            parent: The owning ``BaseSandbox`` component — used to open
                the log-forwarding ``LoggingContext`` on ``__enter__``.
            forward_logs: If True, sandbox stdout/stderr is auto-routed
                into ZenML step logs as a per-session log source.
        """
        self.id = id
        self._parent = parent
        self._forward_logs = forward_logs
        self._log_ctx: Any = None

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

        Subclasses must call ``self._close_log_ctx()`` from their override
        to release the log-forwarding context opened in ``__enter__``.

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

        Hook called from ``__enter__`` before the log-forwarding context
        opens. Records ``sandbox_session_id``, ``sandbox_flavor``, and
        (when ``_dashboard_url()`` returns a non-None value)
        ``sandbox_dashboard_url`` typed as ``Uri`` on the active step.

        No-ops gracefully when called outside a step context (e.g.
        ad-hoc usage from a script) — ``log_metadata`` raises
        ``ValueError`` which we log at DEBUG. Any other failure
        (network, serialization) is logged at WARNING so it's debuggable
        without breaking sandbox usage.
        """
        from zenml.metadata.metadata_types import MetadataType, Uri
        from zenml.utils.metadata_utils import log_metadata

        metadata: Dict[str, MetadataType] = {
            "sandbox_session_id": self.id,
            "sandbox_flavor": self._parent.flavor,
        }
        url = self._dashboard_url()
        if url:
            metadata["sandbox_dashboard_url"] = Uri(url)
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

    def _close_log_ctx(self) -> None:
        """Releases the log-forwarding ``LoggingContext`` if one is open.

        Idempotent. Subclasses call this from their ``close()`` impl so
        the lifecycle invariant ("opened once on __enter__, closed
        once on close()") lives in one place.
        """
        if self._log_ctx is not None:
            try:
                self._log_ctx.__exit__(None, None, None)
            finally:
                self._log_ctx = None

    def __enter__(self) -> "SandboxSession":
        """Publishes step metadata then opens the log-forwarding context.

        Metadata fires first so a failure here can't leak ``_log_ctx``.
        Idempotent against double-entry: if a log context is already
        open, we don't open a second one — that would orphan the first.

        Returns:
            This session.
        """
        self._on_enter()
        if self._forward_logs and self._log_ctx is None:
            self._log_ctx = self._parent.forward_session_logs(self.id)
            self._log_ctx.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        """Releases the local handle on context-manager exit.

        Args:
            *args: Exception info; ignored — ``close()`` is best-effort.
        """
        self.close()
