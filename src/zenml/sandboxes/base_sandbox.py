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
"""Base abstractions for ZenML sandbox stack components.

A Sandbox is a stack component a step *uses* (not one that runs the step) to
execute code in an isolated environment. See ``plan.md`` and ADR 0001 for the
component-vs-launcher framing rationale.
"""

from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from pydantic import BaseModel, Field

from zenml.config.base_settings import BaseSettings
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponent, StackComponentConfig

logger = get_logger(__name__)


# Sentinel: when used as ``base_image``, the Session uses the image the
# current ZenML step is running in. Falls back to flavor default with a
# warning if the step is not containerized. See plan.md "Session Environment".
STEP_IMAGE = "<step>"


class SandboxExecError(RuntimeError):
    """Raised when a sandbox command fails to launch.

    Once a ``SandboxProcess`` has been returned by ``exec()``, runtime errors
    flow through ``exit_code`` / ``stderr()`` instead of this exception.
    """


class BaseSandboxSnapshot(BaseModel):
    """Serializable handle to a captured Sandbox Session state.

    Round-trips via ``session.snapshot() → BaseSandboxSnapshot`` and
    ``sandbox.restore(snapshot) → SandboxSession``. Each flavor subclasses
    this model and ships a dedicated materializer for it.

    The ``provider`` field must match the flavor name; ``BaseSandbox.restore``
    rejects cross-flavor snapshots.
    """

    provider: str = Field(
        description="Flavor name that produced this snapshot (e.g. 'modal'). "
        "Snapshots cannot be restored across flavors."
    )
    ref: str = Field(
        description="Provider-specific reference (e.g. a Modal Image id, a "
        "k8s checkpoint resource name). Opaque to ZenML."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional auxiliary fields (created_at, size, cost) the "
        "flavor wants preserved with the snapshot.",
    )


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


class SandboxSession(ABC):
    """A live, bounded interaction with a single isolated execution environment.

    Sessions are created by ``BaseSandbox.create_session()``, accept many
    ``exec`` calls, and are closed with ``close()`` (releases handle; sandbox
    keeps running on the provider until its TTL) or ``destroy()`` (terminates
    the sandbox on the provider). The framework does **not** auto-close
    Sessions on step exit — see ADR 0002 for why this matters for the
    subagent-attach flow.
    """

    id: str

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

    def __enter__(self) -> "SandboxSession":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class BaseSandboxConfig(StackComponentConfig):
    """Base configuration for sandbox stack components.

    Default env vars and stored secrets that should be injected into every
    Session are configured on the StackComponent itself, not here — see
    ``StackComponent.environment`` and ``StackComponent.secrets`` (set via
    ``zenml stack-component register --env ... --secret ...``). Flavors read
    those at ``create_session()`` time and pass them through to the provider.
    """

    @property
    def is_remote(self) -> bool:
        """Sandboxes are called from inside step code, not from the server.

        Unlike orchestrators and step operators, the ZenML server does not
        need to reach the sandbox.
        """
        return False

    @property
    def is_local(self) -> bool:
        return not self.is_remote


class BaseSandboxSettings(BaseSettings):
    """Per-step / per-pipeline overrides for a Sandbox component."""

    base_image: Optional[str] = Field(
        default=None,
        description="Image for the Session. None → flavor default; the "
        "sentinel STEP_IMAGE → image the current ZenML step is running in "
        "(warns and falls back to flavor default if not containerized); "
        "any other string → exact image URI.",
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-step env vars merged into the Session on top of the "
        "component's `StackComponent.environment` (settings override on key "
        "collision). Values may reference ZenML secrets via "
        "{{secret_name.key}}.",
    )
    copy_local_env: bool = Field(
        default=False,
        description="If True, propagates the step process's full local env "
        "(including any resolved ZenML secrets present) into the Session. "
        "Convenient for prototyping; off by default for security.",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Session-level timeout passed through to the provider's "
        "TTL knob. None lets the provider apply its own default.",
    )
    forward_logs_to_step: Optional[bool] = Field(
        default=None,
        description="If True, sandbox stdout/stderr is auto-forwarded into "
        "ZenML's step logs as a dedicated log source tagged with the "
        "session id (visible as a separate stream in the UI). Disable to "
        "skip the forwarding overhead. None (default) lets the flavor "
        "decide: True when base_image is STEP_IMAGE (ZenML deps available), "
        "False otherwise.",
    )


class BaseSandbox(StackComponent, ABC):
    """Base class for all ZenML sandbox components.

    See ADR 0001 (component-vs-launcher) and ADR 0002 (attach vs restore) in
    ``plan.md``.
    """

    @property
    def config(self) -> BaseSandboxConfig:
        return cast(BaseSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        return BaseSandboxSettings

    @abstractmethod
    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a fresh Session, applying config + settings.

        Implementations merge ``self.config.environment`` (defaults) with
        ``settings.environment`` (overrides on key collision) before applying
        to the provider. ``settings`` may also override ``base_image``,
        ``timeout_seconds``, etc.
        """

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnects to an already-live Session by id.

        Cheap (no snapshot needed). Use for subagent / cross-pipeline flows.
        Optional; default raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support session attach."
        )

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Materializes a new Session from a stored Snapshot.

        Returns a *new* Session (fresh id); the original is unaffected.
        Validates ``snapshot.provider`` matches this flavor before delegating.
        Subclasses should call ``super().restore(snapshot)`` first.
        """
        if snapshot.provider != self.flavor:
            raise ValueError(
                f"Cannot restore snapshot from provider '{snapshot.provider}' "
                f"on a '{self.flavor}' sandbox component."
            )
        raise NotImplementedError(
            f"{type(self).__name__} does not support restore."
        )


class BaseSandboxFlavor(Flavor):
    """Base flavor contract for sandbox implementations."""

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.SANDBOX

    @property
    def config_class(self) -> Type[BaseSandboxConfig]:
        return BaseSandboxConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseSandbox]:
        """Concrete BaseSandbox subclass implementing this flavor."""
