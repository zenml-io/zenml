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
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Generator,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
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


# Default cap for ``SandboxProcess.collect`` — 1 MiB per stream is enough
# for typical agent tool output (a printed answer, an exception traceback,
# a small dataframe dump) without swamping the LLM's context window or
# returning megabytes of data through the tool call.
_DEFAULT_COLLECT_BYTES = 1_048_576


@dataclass
class SandboxOutput:
    """Result of fully consuming a ``SandboxProcess``.

    Returned by ``SandboxProcess.collect()``. Carries both stdout and
    stderr as captured strings plus the exit code, along with per-stream
    truncation flags so callers can tell when they hit the byte cap.
    """

    stdout: str
    stderr: str
    exit_code: int
    stdout_truncated: bool = False
    stderr_truncated: bool = False


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

    def collect(
        self, *, max_bytes: int = _DEFAULT_COLLECT_BYTES
    ) -> SandboxOutput:
        """Fully drains stdout + stderr, blocks until exit, returns everything.

        This is the typical convenience for agent-tool callers: replaces
        the ``stdout = ...; stderr = ...; code = wait()`` dance with one
        call that returns a ``SandboxOutput``. Both streams are drained
        to completion (so ``wait()`` is safe to call even when the
        underlying provider holds output in a buffered reader); output
        beyond ``max_bytes`` per stream is dropped and the corresponding
        ``*_truncated`` flag is set so callers know.

        For full streaming control, iterate ``stdout()`` / ``stderr()``
        directly instead.

        Args:
            max_bytes: Soft cap per stream. Default 1 MiB.

        Returns:
            A ``SandboxOutput`` with captured stdout, stderr, exit code,
            and per-stream truncation flags.
        """
        stdout, stdout_truncated = _drain_capped(self.stdout(), max_bytes)
        stderr, stderr_truncated = _drain_capped(self.stderr(), max_bytes)
        exit_code = self.wait()
        return SandboxOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )


def _drain_capped(stream: Iterator[str], max_bytes: int) -> Tuple[str, bool]:
    """Drain a line iterator fully, capping the returned string at ``max_bytes``.

    Always consumes to completion (StopIteration) so the underlying
    provider's wait() is not blocked. Lines that would push the total
    over ``max_bytes`` are dropped, but iteration continues.

    Args:
        stream: Source iterator (line-delimited strings).
        max_bytes: Soft cap on the returned string length.

    Returns:
        Tuple of ``(joined_string, truncated_flag)``.
    """
    parts: List[str] = []
    total = 0
    truncated = False
    for line in stream:
        total += len(line)
        if total > max_bytes:
            truncated = True
            continue
        parts.append(line)
    return "".join(parts), truncated


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
        """Returns self so the Session can be used as a context manager.

        Returns:
            This session.
        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Releases the local handle on context-manager exit.

        Args:
            *args: Exception info; ignored — ``close()`` is best-effort.
        """
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
        """Inverse of ``is_remote``.

        Returns:
            Whether this sandbox component is local-only.
        """
        return not self.is_remote


class BaseSandboxSettings(BaseSettings):
    """Per-step / per-pipeline overrides for a Sandbox component."""

    base_image: Optional[str] = Field(
        default=None,
        description="Image for the Session. None → flavor default; the "
        "sentinel STEP_IMAGE → image the current ZenML step is running in "
        "(warns and falls back to flavor default if not containerized); "
        "any other string → exact image URI. STEP_IMAGE resolution only "
        "fires for static containerized pipelines (the non-dynamic submit "
        "path); dynamic pipelines and the legacy prepare_or_run_pipeline "
        "path silently fall back to the flavor default.",
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
        "Layered FIRST in the env merge — explicit component env, "
        "component secrets, and per-step settings.environment all override "
        "values copied from the local env. Convenient for prototyping; off "
        "by default for security.",
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
        """Typed sandbox component configuration.

        Returns:
            The component's config.
        """
        return cast(BaseSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for per-step / per-pipeline overrides.

        Returns:
            ``BaseSandboxSettings``. Flavors may override to expose
            flavor-specific fields.
        """
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

    def resolve_forward_logs_to_step(
        self, settings: BaseSandboxSettings
    ) -> bool:
        """Resolves the effective ``forward_logs_to_step`` value.

        When the user leaves the setting as ``None`` (default), the flavor
        decides: ``True`` only when ``base_image == STEP_IMAGE`` (the
        sandbox is running the step's own image and is "integrated");
        ``False`` for the flavor default image or any custom image
        (sandbox is "alien" — don't assume the user wants their logs
        intermingled).

        Args:
            settings: Effective per-step settings.

        Returns:
            The resolved boolean.
        """
        if settings.forward_logs_to_step is not None:
            return settings.forward_logs_to_step
        return settings.base_image == STEP_IMAGE

    @contextmanager
    def forward_session_logs(
        self, session_id: str
    ) -> Generator[None, None, None]:
        """Opens a ZenML log context for a Session's stdout/stderr stream.

        Flavors wrap their ``create_session()`` / ``exec`` integration with
        this context manager when ``resolve_forward_logs_to_step`` is
        ``True``. Sandbox output emitted through ``logger.info`` /
        ``logger.warning`` inside this block lands as a dedicated log
        source ``f"sandbox:{session_id}"`` in the step's log stream.

        No-ops gracefully if step logging is globally disabled (e.g.
        ``ZENML_DISABLE_STEP_LOGS_STORAGE=1``) or the active stack has no
        reachable log store (e.g. script-mode usage). The wrapped block
        still runs in both cases.

        Args:
            session_id: Stable id of the Session being forwarded.

        Yields:
            ``None``.
        """
        from zenml.utils.logging_utils import setup_logging_context

        try:
            ctx = setup_logging_context(source=f"sandbox:{session_id}")
        except Exception as e:
            logger.debug(
                "Sandbox log forwarding disabled: %s. Falling back to "
                "plain logger.",
                e,
            )
            yield
            return

        with ctx:
            yield

    @staticmethod
    def forward_lines(
        lines: Iterator[str],
        *,
        stream: Literal["stdout", "stderr"] = "stdout",
    ) -> Iterator[str]:
        """Side-effects each yielded line through the Python logger.

        Used by flavors to plug a Session's stdout/stderr iterator into
        the active ``LoggingContext`` without changing the iterator
        contract — callers still get back each line.

        Args:
            lines: Source iterator (line-delimited strings).
            stream: ``"stdout"`` → INFO, ``"stderr"`` → WARNING.

        Yields:
            Each line from the source iterator unchanged.
        """
        log_fn = logger.info if stream == "stdout" else logger.warning
        for line in lines:
            log_fn(line.rstrip("\n"))
            yield line

    def _resolve_session_environment(
        self, settings: Optional[BaseSandboxSettings]
    ) -> Dict[str, str]:
        """Merges env vars from all sources for a new Session.

        Order (later sources override earlier on key collision — most-specific
        wins, matching ``get_runtime_environment`` precedent):

        1. ``os.environ`` of the step process, if ``settings.copy_local_env``
           is ``True``. Layered first so explicit configuration always wins.
        2. ``StackComponent.environment`` (component-level explicit env vars).
        3. Each UUID in ``StackComponent.secrets`` resolved via the ZenML
           secret store and exploded into env vars (every key in the secret
           becomes one ``$KEY=value`` entry).
        4. ``settings.environment`` — per-step overrides. Values may be ZenML
           ``{{secret_name.key}}`` references, resolved here. Highest
           precedence.

        Args:
            settings: Effective per-step settings, or ``None`` (use defaults).

        Returns:
            The merged ``Dict[str, str]`` to pass to the provider.
        """
        import os

        from zenml.client import Client
        from zenml.utils import secret_utils

        merged: Dict[str, str] = {}

        # 1. Local env first — explicit configuration below will overwrite.
        if settings is not None and settings.copy_local_env:
            merged.update(os.environ)

        # 2. Component-level explicit env vars.
        merged.update(self.environment or {})

        # 3. Component-level secrets exploded.
        client: Optional["Client"] = None
        if self.secrets or (settings is not None and settings.environment):
            client = Client()

        if self.secrets and client is not None:
            for secret_id in self.secrets:
                try:
                    secret = client.get_secret(secret_id)
                except Exception as e:
                    logger.warning(
                        "Could not resolve sandbox component secret %s: %s. "
                        "Skipping.",
                        secret_id,
                        e,
                    )
                    continue
                merged.update(secret.secret_values)

        # 4. Per-step overrides (highest precedence). Secret references
        # in values get resolved against the secret store.
        if (
            settings is not None
            and settings.environment
            and client is not None
        ):
            for key, value in settings.environment.items():
                if secret_utils.is_secret_reference(value):
                    ref = secret_utils.parse_secret_reference(value)
                    try:
                        secret = client.get_secret_by_name_and_private_status(
                            name=ref.name
                        )
                        merged[key] = secret.secret_values[ref.key]
                    except Exception as e:
                        logger.warning(
                            "Could not resolve secret reference %r for env "
                            "var '%s': %s. Skipping.",
                            value,
                            key,
                            e,
                        )
                else:
                    merged[key] = value

        return merged

    def _validate_snapshot_provider(
        self, snapshot: BaseSandboxSnapshot
    ) -> None:
        """Asserts a snapshot was produced by this component's flavor.

        Subclasses that implement ``restore`` call this helper first to
        reject cross-flavor snapshots with a clear error message before
        invoking their provider's restore primitive.

        Args:
            snapshot: The snapshot to validate.

        Raises:
            ValueError: If ``snapshot.provider`` does not match this
                component's flavor.
        """
        if snapshot.provider != self.flavor:
            raise ValueError(
                f"Cannot restore snapshot from provider '{snapshot.provider}' "
                f"on a '{self.flavor}' sandbox component."
            )

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Materializes a new Session from a stored Snapshot.

        Returns a *new* Session (fresh id); the original is unaffected.
        Subclasses that support restore should call
        ``self._validate_snapshot_provider(snapshot)`` first, then
        materialize from the provider primitive.

        Args:
            snapshot: The snapshot to restore from.

        Returns:
            A new ``SandboxSession`` materialized from the snapshot.

        Raises:
            NotImplementedError: Default — flavors opt in by overriding.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support restore."
        )


class BaseSandboxFlavor(Flavor):
    """Base flavor contract for sandbox implementations."""

    @property
    def type(self) -> StackComponentType:
        """Stack component type for all sandbox flavors.

        Returns:
            ``StackComponentType.SANDBOX``.
        """
        return StackComponentType.SANDBOX

    @property
    def config_class(self) -> Type[BaseSandboxConfig]:
        """Configuration class for this flavor.

        Returns:
            The config class (subclasses may override).
        """
        return BaseSandboxConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseSandbox]:
        """Concrete BaseSandbox subclass implementing this flavor."""
