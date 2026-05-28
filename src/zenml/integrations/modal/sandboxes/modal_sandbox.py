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
"""Modal sandbox flavor implementation.

Wraps Modal's ``Sandbox`` / ``ContainerProcess`` / ``Image`` primitives in the
``BaseSandbox`` interface.

Modal exposes a synchronous Sandbox API (modal>=0.64). Streaming output is
returned as a ``LogsReader`` iterable that yields byte chunks (not lines); we
line-buffer it to satisfy ``SandboxProcess.stdout()`` / ``stderr()`` contracts.
"""

import os
import shlex
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Type,
    Union,
    cast,
)

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal.flavors import (
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    STEP_IMAGE,
    BaseSandbox,
    BaseSandboxSettings,
    BaseSandboxSnapshot,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
)

if TYPE_CHECKING:
    import modal  # noqa: F401

    from zenml.config import ResourceSettings

logger = get_logger(__name__)


class ModalSandboxSnapshot(BaseSandboxSnapshot):
    """Snapshot of a Modal Sandbox's filesystem.

    Modal's ``snapshot_filesystem()`` captures the FS only — no in-memory
    process state. ``restore`` boots a *new* Sandbox from the stored Image.

    ``provider`` is locked to ``"modal"`` via ``Literal`` — Pydantic rejects
    any other value at construction time, so callers can't mint a snapshot
    that lies about its flavor.
    """

    provider: Literal["modal"] = Field(default="modal")


def _line_buffer(chunks: Iterable[Any]) -> Iterator[str]:
    """Re-emits byte/str chunks one decoded line at a time.

    Yields lines including their trailing newline when present. A final
    line without ``\\n`` is yielded once the underlying iterable is
    exhausted. Mirrors ``SandboxProcess.stdout()`` contract — lines, utf-8.
    """
    buffer = ""
    for chunk in chunks:
        if chunk is None:
            continue
        if isinstance(chunk, bytes):
            text = chunk.decode("utf-8", errors="replace")
        else:
            text = str(chunk)
        buffer += text
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            yield line + "\n"
    if buffer:
        yield buffer


class ModalSandboxProcess(SandboxProcess):
    """Wraps a Modal ``ContainerProcess`` in the ``SandboxProcess`` interface."""

    def __init__(
        self,
        process: Any,
        *,
        session: Optional["ModalSandboxSession"] = None,
    ) -> None:
        """Initializes the process wrapper.

        Args:
            process: The Modal ``ContainerProcess`` returned by ``sandbox.exec``.
            session: Owning session. When provided, stdout/stderr lines
                are forwarded through ``session._wrap_stream`` so they
                land in the per-session sandbox log source.
        """
        self._process = process
        self._session = session

    def stdout(self) -> Iterator[str]:
        """Returns a line-buffered stdout iterator, log-wrapped when bound.

        Returns:
            Plain line iterator when no session is attached; otherwise
            wrapped via ``session._wrap_stream`` so each line is also
            emitted to the sandbox log source.
        """
        lines = _line_buffer(self._process.stdout)
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stdout")

    def stderr(self) -> Iterator[str]:
        """Returns a line-buffered stderr iterator, log-wrapped when bound.

        Returns:
            Plain line iterator when no session is attached; otherwise
            wrapped via ``session._wrap_stream`` so each line is also
            emitted to the sandbox log source at WARNING level.
        """
        lines = _line_buffer(self._process.stderr)
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stderr")

    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the command exits.

        Args:
            timeout: Not supported. Modal's ``ContainerProcess.wait()``
                doesn't accept a timeout in the public API. Passing a
                non-None value raises rather than silently ignoring —
                use the Session-level ``timeout_seconds`` setting to
                bound total Session lifetime.

        Returns:
            The exit code.

        Raises:
            NotImplementedError: If ``timeout`` is not ``None``.
        """
        if timeout is not None:
            raise NotImplementedError(
                "Modal does not support per-exec timeouts. Use "
                "ModalSandboxSettings.timeout_seconds for Session-level "
                "TTL, or wrap the wait call in your own watchdog."
            )
        self._process.wait()
        return int(self._process.returncode or 0)

    def kill(self) -> None:
        """Best-effort process termination.

        Modal's ``ContainerProcess`` does not expose a per-command kill in
        the public API (``wait`` / ``poll`` / ``stdin`` / ``stdout`` /
        ``stderr`` / ``attach`` only — see ``modal.container_process``).
        We close stdin to signal EOF, which lets well-behaved processes
        exit cleanly. For a hard kill, call ``ModalSandboxSession.destroy()``
        to terminate the entire Sandbox.
        """
        try:
            if self._process.stdin is not None:
                self._process.stdin.close()
        except Exception as e:
            logger.warning(
                "Closing Modal process stdin during kill() failed: %s. "
                "The process may still be running.",
                e,
                exc_info=True,
            )
        logger.warning(
            "Modal does not support per-command kill; closed stdin instead. "
            "Use session.destroy() to force-terminate the whole Sandbox."
        )

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code, or ``None`` if the command is still running.

        Returns:
            The exit code or ``None``.
        """
        code = self._process.returncode
        return int(code) if code is not None else None


class ModalSandboxSession(SandboxSession):
    """Wraps a Modal ``Sandbox`` in the ``SandboxSession`` interface."""

    def __init__(
        self,
        sandbox: Any,
        *,
        parent: "BaseSandbox",
    ) -> None:
        """Initializes the session wrapper.

        Args:
            sandbox: The live Modal ``Sandbox`` object.
            parent: The owning ``BaseSandbox`` component.
        """
        super().__init__(
            id=sandbox.object_id,
            parent=parent,
        )
        self._sandbox = sandbox

    def _dashboard_url(self) -> Optional[str]:
        """Returns the Modal sandbox's dashboard URL, or ``None``.

        Returns:
            URL string from ``Sandbox.get_dashboard_url()`` (older SDKs
            without this API return ``None``).
        """
        try:
            url = self._sandbox.get_dashboard_url()
        except Exception as e:  # noqa: BLE001
            # Older Modal SDKs may not expose get_dashboard_url; tolerable.
            logger.debug(
                "Could not resolve Modal sandbox dashboard URL: %s", e
            )
            return None
        return cast(Optional[str], url)

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Starts a command in the Modal Sandbox.

        Args:
            command: Command to run. ``List[str]`` is passed argv-style;
                a string is shell-split with ``shlex.split``.
            cwd: Working directory inside the sandbox. ``None`` uses the
                Modal default.
            env: Per-exec env vars (in addition to the Session-level env
                injected at create time).

        Returns:
            A ``ModalSandboxProcess`` wrapping the live command handle.
            stdout/stderr iterators emit each line into the dedicated
            ``sandbox:<id>`` log source (alongside a ``$ <command>``
            marker emitted right before launch).

        Raises:
            SandboxExecError: If Modal rejects the launch (e.g. binary not
                found, image broken).
        """
        argv: List[str] = (
            list(command)
            if isinstance(command, list)
            else shlex.split(command)
        )
        # Shell-style marker in the sandbox log source.
        self._log_command(argv)

        kwargs: Dict[str, Any] = {}
        if cwd is not None:
            kwargs["workdir"] = cwd
        if env:
            # Modal expects a ``modal.Secret`` for env injection.
            import modal

            # Modal types env_dict as Dict[str, Optional[str]]; our env is
            # narrower (Dict[str, str]) — valid subtype at runtime, cast for mypy.
            kwargs["secrets"] = [
                modal.Secret.from_dict(cast(Dict[str, Optional[str]], env))
            ]
        started_at = time.time()
        try:
            process = self._sandbox.exec(*argv, **kwargs)
        except Exception as e:
            raise SandboxExecError(
                f"Modal exec failed to launch ({type(e).__name__}): {e}"
            ) from e
        wrapped = ModalSandboxProcess(process, session=self)
        wrapped._started_at = started_at
        return wrapped

    def snapshot(self) -> ModalSandboxSnapshot:
        """Captures the Sandbox's filesystem as a reusable Modal Image.

        Returns:
            A ``ModalSandboxSnapshot`` whose ``ref`` is the Modal Image id.
            No in-memory process state is captured.
        """
        image = self._sandbox.snapshot_filesystem()
        return ModalSandboxSnapshot(ref=image.object_id)

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file into the Sandbox.

        Uses Modal's ``Sandbox.filesystem.copy_from_local()`` API. The
        older ``Sandbox.open() + FileIO.write()`` path is deprecated by
        Modal as of 2026-03-09.

        Args:
            local_path: Path to the file on the caller's machine.
            remote_path: Destination path inside the Sandbox.
        """
        self._sandbox.filesystem.copy_from_local(local_path, remote_path)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the Sandbox to local storage.

        Uses Modal's ``Sandbox.filesystem.copy_to_local()`` API. The
        older ``Sandbox.open() + FileIO.read()`` path is deprecated by
        Modal as of 2026-03-09.

        Args:
            remote_path: Source path inside the Sandbox.
            local_path: Destination path on the caller's machine.
        """
        self._sandbox.filesystem.copy_to_local(remote_path, local_path)

    def close(self) -> None:
        """Releases the local handle and tears down the log-forwarding context.

        Modal's ``Sandbox`` is a stateless client handle (no socket to
        drop). Idempotent — safe to call multiple times, and safe to
        call outside a ``with`` block. The Sandbox keeps running on
        Modal until its TTL expires; use ``destroy()`` to force-stop
        immediately.
        """
        self._close_log_ctx()

    def destroy(self) -> None:
        """Terminates the Sandbox on Modal."""
        try:
            self._sandbox.terminate()
        except Exception as e:
            logger.warning(
                "Modal sandbox terminate() failed: %s. The sandbox may "
                "still be running; Modal will eventually clean it up "
                "via its TTL.",
                e,
                exc_info=True,
            )


def _resolve_image(
    base_image: Optional[str], default_image: str
) -> "modal.Image":
    """Resolves a base_image setting into a concrete Modal Image.

    Args:
        base_image: The setting value (``None``, ``STEP_IMAGE``, or a URI).
        default_image: Fallback image URI from the component config.

    Returns:
        A ``modal.Image`` instance ready to pass to ``Sandbox.create``.
    """
    import modal

    if base_image is None:
        return modal.Image.from_registry(default_image)
    if base_image == STEP_IMAGE:
        step_image = _resolve_step_image()
        if not step_image:
            logger.warning(
                "STEP_IMAGE requested but the current step is not "
                "running on a containerized orchestrator with a built "
                "image; falling back to the flavor's default image '%s'.",
                default_image,
            )
            return modal.Image.from_registry(default_image)
        return modal.Image.from_registry(step_image)
    return modal.Image.from_registry(base_image)


def _resolve_step_image() -> Optional[str]:
    """Returns the image URI of the currently-running step, if any.

    Looks up the snapshot attached to the active pipeline run via
    ``StepContext`` and delegates to ``ContainerizedOrchestrator.get_image``
    (the same helper the orchestrator uses to pick images at submit time).
    Returns ``None`` when there's no step context, no snapshot, no build,
    or the active orchestrator isn't containerized.

    Returns:
        The image URI for the current step, or ``None``.
    """
    from zenml.orchestrators.containerized_orchestrator import (
        ContainerizedOrchestrator,
    )
    from zenml.steps.step_context import StepContext

    ctx = StepContext.get()
    if ctx is None:
        return None
    snapshot = ctx.pipeline_run.snapshot
    if snapshot is None or snapshot.build is None:
        return None
    try:
        return ContainerizedOrchestrator.get_image(
            snapshot=snapshot, step_name=ctx.step_name
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("Could not resolve step image: %s", e)
        return None


class ModalSandbox(BaseSandbox):
    """Sandbox flavor backed by Modal."""

    # Lazily-cached Modal App handle. Looking it up is a network round-trip;
    # we cache after the first create_session/restore call.
    _app: Optional[Any] = None

    @property
    def config(self) -> ModalSandboxConfig:
        """Typed config.

        Returns:
            The component's Modal-specific config.
        """
        return cast(ModalSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class — Modal extends the base with gpu/cpu/memory etc.

        Returns:
            ``ModalSandboxSettings``.
        """
        return ModalSandboxSettings

    def _export_modal_tokens(self) -> None:
        """Exports config-carried Modal credentials into ``os.environ``.

        Modal authenticates from ``~/.modal.toml`` or the
        ``MODAL_TOKEN_ID`` / ``MODAL_TOKEN_SECRET`` env vars. For step
        processes running in remote orchestrators (Kubernetes,
        SageMaker, etc.) the local toml isn't available, so we let
        users attach the tokens to the component config (as
        ``SecretField``s) and export them here just before importing
        modal. Safe to call multiple times; no-op when both fields are
        unset.
        """
        token_id = self.config.token_id
        token_secret = self.config.token_secret
        if token_id:
            os.environ.setdefault("MODAL_TOKEN_ID", token_id)
        if token_secret:
            os.environ.setdefault("MODAL_TOKEN_SECRET", token_secret)

    def _get_app(self) -> Any:
        """Returns this component's Modal ``App``, looking it up once and caching.

        Returns:
            The Modal App.
        """
        if self._app is None:
            self._export_modal_tokens()
            import modal

            self._app = modal.App.lookup(
                self.config.app_name, create_if_missing=True
            )
        return self._app

    def _modal_sandbox_kwargs(
        self,
        eff: ModalSandboxSettings,
        *,
        with_env: bool = True,
    ) -> Dict[str, Any]:
        """Builds the kwargs passed to ``modal.Sandbox.create``.

        Used by both ``create_session`` and ``restore`` so the same
        timeout / resource / region knobs apply uniformly. Resource
        knobs (cpu, memory, gpu count) are read from the active step's
        ``ResourceSettings`` and combined with this flavor's gpu
        type via ``get_gpu_values`` — the same helper the Modal step
        operator uses, so the two components stay consistent.

        Args:
            eff: Effective per-step settings.
            with_env: If True, the resolved Session env is exported as
                a Modal Secret. Skipped on the restore path where
                injecting env into a frozen filesystem image is rarely
                what the caller wants.

        Returns:
            Kwargs for ``modal.Sandbox.create``.
        """
        import modal

        from zenml.config.resource_settings import ByteUnit

        resource_settings = self._active_resource_settings()
        memory_mb = resource_settings.get_memory(ByteUnit.MB)

        # GPU value combines the Modal-specific type ("A100", "H100", ...)
        # with the count from ResourceSettings ("A100:2"). Mirrors what
        # ModalStepOperator does so the two components stay consistent.
        gpu_values: Optional[str] = None
        if eff.gpu:
            gpu_values = (
                f"{eff.gpu}:{resource_settings.gpu_count}"
                if resource_settings.gpu_count
                else eff.gpu
            )

        kwargs: Dict[str, Any] = {"app": self._get_app()}
        if with_env:
            env = self._resolve_session_environment(eff)
            if env:
                # Modal types env_dict as Dict[str, Optional[str]]; our
                # env is narrower (Dict[str, str]). Valid subtype at
                # runtime, cast for mypy.
                kwargs["secrets"] = [
                    modal.Secret.from_dict(cast(Dict[str, Optional[str]], env))
                ]
        if eff.timeout_seconds is not None:
            kwargs["timeout"] = eff.timeout_seconds
        if gpu_values is not None:
            kwargs["gpu"] = gpu_values
        if resource_settings.cpu_count is not None:
            kwargs["cpu"] = resource_settings.cpu_count
        if memory_mb is not None:
            kwargs["memory"] = int(memory_mb)
        if eff.region is not None:
            kwargs["region"] = eff.region
        if eff.cloud is not None:
            kwargs["cloud"] = eff.cloud
        return kwargs

    @staticmethod
    def _active_resource_settings() -> "ResourceSettings":
        """Returns the active step's ``ResourceSettings``, or defaults.

        Reads from the active ``StepContext``'s step config. When no step
        context is available (ad-hoc sandbox usage from a script),
        returns an empty ``ResourceSettings`` so the caller can still
        compose Modal kwargs without erroring.

        Returns:
            The step's resource settings (cpu_count, memory, gpu_count).
        """
        from zenml.config import ResourceSettings
        from zenml.steps.step_context import StepContext

        ctx = StepContext.get()
        if ctx is None:
            return ResourceSettings()
        return ctx.step_run.config.resource_settings

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Boots a fresh Modal Sandbox.

        Args:
            settings: Optional per-step overrides for image / resources / env.

        Returns:
            A ``ModalSandboxSession`` wrapping the live Modal Sandbox.
        """
        self._export_modal_tokens()
        import modal

        eff = cast(ModalSandboxSettings, self.resolve_settings(settings))
        image = _resolve_image(eff.base_image, self.config.default_image)

        sandbox = modal.Sandbox.create(
            image=image, **self._modal_sandbox_kwargs(eff)
        )
        return ModalSandboxSession(sandbox, parent=self)

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnects to a still-live Modal Sandbox by id.

        Args:
            session_id: The Modal sandbox object id (e.g. ``sb_xxx``).

        Returns:
            A ``ModalSandboxSession`` wrapping the existing live sandbox.

        Raises:
            RuntimeError: If Modal can't find a sandbox with the given id
                (terminated or unknown). Wraps the underlying Modal error
                so callers get a stable exception type with a clear message.
        """
        # Export tokens before any Modal call, otherwise users on
        # remote orchestrators with no local ~/.modal.toml can't attach.
        self._export_modal_tokens()
        import modal

        try:
            sandbox = modal.Sandbox.from_id(session_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to attach to Modal sandbox '{session_id}' "
                f"({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxSession(sandbox, parent=self)

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Boots a new Session from a stored filesystem snapshot.

        Applies the same timeout / resource / region settings as
        ``create_session``. Env injection is skipped: a restored
        sandbox boots from a frozen Image and the caller almost never
        wants to layer a fresh env merge on top.

        Args:
            snapshot: A ``ModalSandboxSnapshot`` whose ``ref`` is a Modal
                Image id captured via ``snapshot_filesystem()``.

        Returns:
            A new ``ModalSandboxSession`` initialized from the Image. No
            in-memory state from the original Session is preserved.

        Raises:
            RuntimeError: If Modal can't load the Image (e.g. id GC'd).
        """
        self._validate_snapshot_provider(snapshot)
        self._export_modal_tokens()
        import modal

        eff = cast(ModalSandboxSettings, self.resolve_settings(None))
        try:
            image = modal.Image.from_id(snapshot.ref)
            sandbox = modal.Sandbox.create(
                image=image,
                **self._modal_sandbox_kwargs(eff, with_env=False),
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to restore Modal sandbox from image "
                f"'{snapshot.ref}' ({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxSession(sandbox, parent=self)
