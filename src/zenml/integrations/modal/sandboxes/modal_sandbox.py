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
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Union,
    cast,
)

from pydantic import Field

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

logger = get_logger(__name__)


# Env var the orchestrator entrypoint sets when a step runs in a container.
# Used to resolve the STEP_IMAGE sentinel — see plan.md.
_STEP_IMAGE_ENV_VAR = "ZENML_ACTIVE_STEP_IMAGE"


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

    def __init__(self, process: Any, *, forward_logs: bool = False) -> None:
        """Initializes the process wrapper.

        Args:
            process: The Modal ``ContainerProcess`` returned by ``sandbox.exec``.
            forward_logs: If True, each yielded stdout/stderr line is also
                side-effected through the Python logger (via
                ``BaseSandbox.forward_lines``). Combined with the Session's
                ``forward_session_logs`` context manager, this routes
                sandbox output into ZenML's step log stream tagged with the
                session id.
        """
        self._process = process
        self._forward_logs = forward_logs

    def stdout(self) -> Iterator[str]:
        """Line-buffered stdout iterator.

        Yields:
            Lines of stdout output, with trailing newlines preserved.
        """
        lines = _line_buffer(self._process.stdout)
        if self._forward_logs:
            return BaseSandbox.forward_lines(lines, stream="stdout")
        return lines

    def stderr(self) -> Iterator[str]:
        """Line-buffered stderr iterator.

        Yields:
            Lines of stderr output, with trailing newlines preserved.
        """
        lines = _line_buffer(self._process.stderr)
        if self._forward_logs:
            return BaseSandbox.forward_lines(lines, stream="stderr")
        return lines

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
        parent: Optional["BaseSandbox"] = None,
        forward_logs: bool = False,
    ) -> None:
        """Initializes the session wrapper.

        Args:
            sandbox: The live Modal ``Sandbox`` object.
            parent: The owning ``BaseSandbox`` component. Used to open
                the log-forwarding ``LoggingContext`` when entering the
                Session as a context manager. Pass ``None`` for the
                ``attach()`` / ``restore()`` paths where no parent is
                relevant.
            forward_logs: If True, sandbox stdout/stderr is auto-routed
                into ZenML step logs as a per-session log source. The
                ``LoggingContext`` is opened on ``__enter__`` and closed
                on ``__exit__``; outside a ``with`` block the flag has
                no effect.
        """
        self._sandbox = sandbox
        self.id = sandbox.object_id
        self._parent = parent
        self._forward_logs = forward_logs
        self._log_ctx: Any = None

    def __enter__(self) -> "ModalSandboxSession":
        """Opens the log-forwarding context if enabled.

        Returns:
            This session.
        """
        if self._forward_logs and self._parent is not None:
            self._log_ctx = self._parent.forward_session_logs(self.id)
            self._log_ctx.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        """Closes the log-forwarding context, then releases the handle.

        Args:
            *args: Exception info; passed through to the underlying
                context manager so it can run any cleanup.
        """
        if self._log_ctx is not None:
            try:
                self._log_ctx.__exit__(*args)
            finally:
                self._log_ctx = None
        self.close()

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
            If the Session was created with ``forward_logs=True``, the
            returned process's ``stdout()`` / ``stderr()`` iterators
            side-effect each line through the Python logger so they
            land in the active ``LoggingContext`` opened on ``__enter__``.

        Raises:
            SandboxExecError: If Modal rejects the launch (e.g. binary not
                found, image broken).
        """
        argv: List[str] = (
            list(command)
            if isinstance(command, list)
            else shlex.split(command)
        )
        kwargs: Dict[str, Any] = {}
        if cwd is not None:
            kwargs["workdir"] = cwd
        if env:
            # Modal expects a ``modal.Secret`` for env injection.
            import modal

            kwargs["secrets"] = [modal.Secret.from_dict(env)]
        try:
            process = self._sandbox.exec(*argv, **kwargs)
        except Exception as e:
            raise SandboxExecError(
                f"Modal exec failed to launch ({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxProcess(process, forward_logs=self._forward_logs)

    def snapshot(self) -> ModalSandboxSnapshot:
        """Captures the Sandbox's filesystem as a reusable Modal Image.

        Returns:
            A ``ModalSandboxSnapshot`` whose ``ref`` is the Modal Image id.
            No in-memory process state is captured.
        """
        image = self._sandbox.snapshot_filesystem()
        return ModalSandboxSnapshot(ref=image.object_id)

    # 1 MiB transfer chunks balance throughput and memory for large files.
    _FILE_CHUNK_SIZE = 1024 * 1024

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file into the Sandbox (streamed in chunks).

        Args:
            local_path: Path to the file on the caller's machine.
            remote_path: Destination path inside the Sandbox.
        """
        with open(local_path, "rb") as src:
            with self._sandbox.open(remote_path, "wb") as dst:
                while chunk := src.read(self._FILE_CHUNK_SIZE):
                    dst.write(chunk)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the Sandbox to local storage (streamed).

        Args:
            remote_path: Source path inside the Sandbox.
            local_path: Destination path on the caller's machine.
        """
        with self._sandbox.open(remote_path, "rb") as src:
            with open(local_path, "wb") as dst:
                while chunk := src.read(self._FILE_CHUNK_SIZE):
                    dst.write(chunk)

    def close(self) -> None:
        """Releases the local handle. The Sandbox keeps running on Modal.

        Modal will eventually terminate the Sandbox per its TTL; use
        ``destroy()`` to force-stop immediately.
        """
        # Nothing to release — modal.Sandbox is just a client-side handle.
        return None

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
        step_image = os.environ.get(_STEP_IMAGE_ENV_VAR)
        if not step_image:
            logger.warning(
                "STEP_IMAGE requested but %s is not set; falling back to "
                "the flavor's default image '%s'.",
                _STEP_IMAGE_ENV_VAR,
                default_image,
            )
            return modal.Image.from_registry(default_image)
        return modal.Image.from_registry(step_image)
    return modal.Image.from_registry(base_image)


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

    def _get_app(self) -> Any:
        """Returns this component's Modal ``App``, looking it up once and caching.

        Returns:
            The Modal App.
        """
        if self._app is None:
            import modal

            self._app = modal.App.lookup(
                self.config.app_name, create_if_missing=True
            )
        return self._app

    def _settings(
        self, override: Optional[BaseSandboxSettings]
    ) -> ModalSandboxSettings:
        """Effective settings = config defaults layered with the override.

        Component-level defaults come from ``self.config`` (which inherits
        from ``ModalSandboxSettings``, so gpu/cpu/memory_mb/region/cloud +
        the base sandbox settings all flow through). Per-step overrides
        win on a per-field basis (only fields explicitly set on the
        override are applied).

        Args:
            override: Optional per-step settings.

        Returns:
            The effective ``ModalSandboxSettings`` for this Session.
        """
        base = self.config.model_dump(
            include=set(ModalSandboxSettings.model_fields.keys())
        )
        if override is not None:
            # ``exclude_unset=True`` so we only apply fields the caller
            # actually set — fixes the bug where Settings defaults
            # silently overwrote Config defaults.
            base.update(override.model_dump(exclude_unset=True))
        return ModalSandboxSettings(**base)

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Boots a fresh Modal Sandbox.

        Args:
            settings: Optional per-step overrides for image / resources / env.

        Returns:
            A ``ModalSandboxSession`` wrapping the live Modal Sandbox.
        """
        import modal

        eff = self._settings(settings)
        image = _resolve_image(eff.base_image, self.config.default_image)
        env = self._resolve_session_environment(eff)

        kwargs: Dict[str, Any] = {"image": image, "app": self._get_app()}
        if env:
            kwargs["secrets"] = [modal.Secret.from_dict(env)]
        if eff.timeout_seconds is not None:
            kwargs["timeout"] = eff.timeout_seconds
        if eff.gpu is not None:
            kwargs["gpu"] = eff.gpu
        if eff.cpu is not None:
            kwargs["cpu"] = eff.cpu
        if eff.memory_mb is not None:
            kwargs["memory"] = eff.memory_mb
        if eff.region is not None:
            kwargs["region"] = eff.region
        if eff.cloud is not None:
            kwargs["cloud"] = eff.cloud

        sandbox = modal.Sandbox.create(**kwargs)
        return ModalSandboxSession(
            sandbox,
            parent=self,
            forward_logs=self.resolve_forward_logs_to_step(eff),
        )

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
        import modal

        try:
            sandbox = modal.Sandbox.from_id(session_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to attach to Modal sandbox '{session_id}' "
                f"({type(e).__name__}): {e}"
            ) from e
        # Reattached sessions don't get log forwarding by default since
        # we don't know the original Settings; callers can wrap manually
        # via `with sandbox.forward_session_logs(session.id):`.
        return ModalSandboxSession(sandbox, parent=self, forward_logs=False)

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Boots a new Session from a stored filesystem snapshot.

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

        import modal

        try:
            image = modal.Image.from_id(snapshot.ref)
            sandbox = modal.Sandbox.create(image=image, app=self._get_app())
        except Exception as e:
            raise RuntimeError(
                f"Failed to restore Modal sandbox from image "
                f"'{snapshot.ref}' ({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxSession(sandbox, parent=self, forward_logs=False)
