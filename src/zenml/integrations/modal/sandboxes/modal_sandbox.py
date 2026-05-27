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
    Optional,
    Union,
    cast,
)

from zenml.client import Client
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
    """

    provider: str = "modal"


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

    def __init__(self, process: Any) -> None:
        """Initializes the process wrapper.

        Args:
            process: The Modal ``ContainerProcess`` returned by ``sandbox.exec``.
        """
        self._process = process

    def stdout(self) -> Iterator[str]:
        """Line-buffered stdout iterator.

        Yields:
            Lines of stdout output, with trailing newlines preserved.
        """
        return _line_buffer(self._process.stdout)

    def stderr(self) -> Iterator[str]:
        """Line-buffered stderr iterator.

        Yields:
            Lines of stderr output, with trailing newlines preserved.
        """
        return _line_buffer(self._process.stderr)

    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the command exits.

        Args:
            timeout: Unused — Modal's ``wait()`` does not accept a timeout
                in the public API. Provided for interface compatibility.

        Returns:
            The exit code.
        """
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
        except Exception:
            logger.debug(
                "Closing Modal process stdin failed; proceeding without."
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

    def __init__(self, sandbox: Any) -> None:
        """Initializes the session wrapper.

        Args:
            sandbox: The live Modal ``Sandbox`` object.
        """
        self._sandbox = sandbox
        self.id = sandbox.object_id

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
            raise SandboxExecError(f"Modal exec failed to launch: {e}") from e
        return ModalSandboxProcess(process)

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

        Args:
            local_path: Path to the file on the caller's machine.
            remote_path: Destination path inside the Sandbox.
        """
        with open(local_path, "rb") as src:
            with self._sandbox.open(remote_path, "wb") as dst:
                dst.write(src.read())

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the Sandbox to local storage.

        Args:
            remote_path: Source path inside the Sandbox.
            local_path: Destination path on the caller's machine.
        """
        with self._sandbox.open(remote_path, "rb") as src:
            with open(local_path, "wb") as dst:
                dst.write(src.read())

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
        except Exception:
            logger.debug(
                "Modal sandbox terminate() failed; likely already stopped."
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


def _resolve_environment(
    component_env: Dict[str, str],
    component_secret_ids: List[Any],
    settings_env: Dict[str, str],
    copy_local_env: bool,
) -> Dict[str, str]:
    """Merges env vars from all sources in the order documented in plan.md.

    Args:
        component_env: ``StackComponent.environment``.
        component_secret_ids: ``StackComponent.secrets`` — ZenML secret UUIDs
            whose keys are exploded into env vars.
        settings_env: ``BaseSandboxSettings.environment``.
        copy_local_env: If True, the step process's local env is layered last.

    Returns:
        The merged ``Dict[str, str]`` env to pass to the provider.
    """
    merged: Dict[str, str] = {}
    merged.update(component_env or {})
    if component_secret_ids:
        client = Client()
        for secret_id in component_secret_ids:
            try:
                secret = client.get_secret(secret_id)
            except Exception as e:
                logger.warning(
                    "Could not resolve sandbox secret %s: %s. Skipping.",
                    secret_id,
                    e,
                )
                continue
            merged.update(secret.secret_values)
    merged.update(settings_env or {})
    if copy_local_env:
        merged.update(os.environ)
    return merged


class ModalSandbox(BaseSandbox):
    """Sandbox flavor backed by Modal."""

    @property
    def config(self) -> ModalSandboxConfig:
        """Typed config.

        Returns:
            The component's Modal-specific config.
        """
        return cast(ModalSandboxConfig, self._config)

    def _settings(
        self, override: Optional[BaseSandboxSettings]
    ) -> ModalSandboxSettings:
        """Merges component-level settings with a per-step override.

        Args:
            override: Optional per-step ``BaseSandboxSettings`` (will be
                upcast / coerced into ``ModalSandboxSettings``).

        Returns:
            The effective ``ModalSandboxSettings`` for this Session.
        """
        if override is None:
            return ModalSandboxSettings(
                **self.config.model_dump(
                    include=set(ModalSandboxSettings.model_fields.keys())
                )
            )
        if isinstance(override, ModalSandboxSettings):
            return override
        return ModalSandboxSettings(**override.model_dump(exclude_none=True))

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
        env = _resolve_environment(
            component_env=self.environment,
            component_secret_ids=self.secrets,
            settings_env=eff.environment,
            copy_local_env=eff.copy_local_env,
        )

        app = modal.App.lookup(self.config.app_name, create_if_missing=True)
        kwargs: Dict[str, Any] = {"image": image, "app": app}
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
        return ModalSandboxSession(sandbox)

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnects to a still-live Modal Sandbox by id.

        Args:
            session_id: The Modal sandbox object id (e.g. ``sb_xxx``).

        Returns:
            A ``ModalSandboxSession`` wrapping the existing live sandbox.
        """
        import modal

        sandbox = modal.Sandbox.from_id(session_id)
        return ModalSandboxSession(sandbox)

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Boots a new Session from a stored filesystem snapshot.

        Args:
            snapshot: A ``ModalSandboxSnapshot`` whose ``ref`` is a Modal
                Image id captured via ``snapshot_filesystem()``.

        Returns:
            A new ``ModalSandboxSession`` initialized from the Image. No
            in-memory state from the original Session is preserved.
        """
        # Provider-equality check is enforced by the base class.
        super_restore = super().restore
        try:
            return super_restore(snapshot)
        except NotImplementedError:
            pass

        import modal

        app = modal.App.lookup(self.config.app_name, create_if_missing=True)
        image = modal.Image.from_id(snapshot.ref)
        sandbox = modal.Sandbox.create(image=image, app=app)
        return ModalSandboxSession(sandbox)
