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
"""Modal sandbox flavor implementation."""

import logging
import shlex
import time
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import modal

from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.modal import sandbox_utils
from zenml.integrations.modal.flavors import (
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.integrations.modal.sandboxes.utils import line_buffer
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxSettings,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
    SandboxSnapshot,
)

if TYPE_CHECKING:
    from modal.container_process import ContainerProcess

logger = get_logger(__name__)


class ModalSandboxProcess(SandboxProcess):
    """Wraps a Modal ``ContainerProcess`` in the ``SandboxProcess`` interface."""

    def __init__(
        self,
        process: "ContainerProcess[str]",
        *,
        session: "ModalSandboxSession",
        started_at: float,
    ) -> None:
        """Initialize the process wrapper.

        Args:
            process: The Modal ``ContainerProcess`` returned by ``sandbox.exec``.
            session: Owning session — stdout/stderr lines forward through
                ``session._wrap_stream`` into the per-session log source.
            started_at: Wall-clock launch time, used by ``collect()`` to
                report elapsed time.
        """
        super().__init__(session=session, started_at=started_at)
        self._process = process

    def stdout(self) -> Iterator[str]:
        """Returns a line-buffered, log-wrapped stdout iterator.

        Returns:
            Line iterator wrapped via ``session._wrap_stream``.
        """
        return self._session._wrap_stream(
            line_buffer(self._process.stdout), log_level=logging.INFO
        )

    def stderr(self) -> Iterator[str]:
        """Returns a line-buffered, log-wrapped stderr iterator.

        Returns:
            Line iterator wrapped via ``session._wrap_stream``.
        """
        return self._session._wrap_stream(
            line_buffer(self._process.stderr), log_level=logging.ERROR
        )

    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the command exits.

        Args:
            timeout: Maximum seconds to wait. Modal's own ``wait()`` has
                no timeout parameter, so a bounded wait polls instead.

        Returns:
            The exit code.

        Raises:
            TimeoutError: If the command is still running after ``timeout``
                seconds.
        """
        if timeout is None:
            self._process.wait()
            return int(self._process.returncode or 0)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            code = self._process.poll()
            if code is not None:
                return int(code)
            time.sleep(0.2)
        raise TimeoutError(
            f"Modal command did not exit within {timeout} seconds."
        )

    def kill(self) -> None:
        """Killing a single command is not supported on Modal.

        Modal's ``ContainerProcess`` exposes no per-command termination
        (only ``poll``/``wait``/``stdin``/``stdout``/``stderr``), and
        tearing down the whole Sandbox to stop one command would also stop
        every other command in the session. Rather than that surprising
        side effect, per-command kill is unsupported; call
        ``session.destroy()`` to stop the entire sandbox.

        Raises:
            NotImplementedError: Always — the Modal SDK has no per-command
                kill.
        """
        raise NotImplementedError(
            "The Modal sandbox cannot kill an individual command: Modal's "
            "ContainerProcess has no per-command termination. Use "
            "session.destroy() to tear down the whole sandbox instead."
        )

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code, or ``None`` if the command is still running.

        Uses ``poll()`` instead of ``returncode``: Modal's
        ``ContainerProcess.returncode`` raises ``InvalidError`` while the
        command is still running, whereas this property promises ``None``.

        Returns:
            The exit code or ``None``.
        """
        code = self._process.poll()
        return int(code) if code is not None else None


class ModalSandboxSession(SandboxSession):
    """Wraps a Modal ``Sandbox`` in the ``SandboxSession`` interface."""

    def __init__(
        self,
        sandbox: "modal.Sandbox",
        *,
        parent: "ModalSandbox",
    ) -> None:
        """Initialize the session wrapper.

        Args:
            sandbox: The live Modal ``Sandbox`` object.
            parent: The owning Modal sandbox component.
        """
        # Assign _sandbox before super().__init__ so the dashboard hook,
        # which is called during base __init__ via _publish_sandbox_metadata,
        # has the state it needs.
        self._sandbox = sandbox
        super().__init__(id=sandbox.object_id, parent=parent)

    def _get_dashboard_url(self) -> Optional[str]:
        """Returns the Modal sandbox's dashboard URL.

        Returns:
            URL string from ``Sandbox.get_dashboard_url()``.
        """
        return cast(Optional[str], self._sandbox.get_dashboard_url())

    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Start a command in the Modal Sandbox.

        Args:
            command: Command to run. A list is passed argv-style; a string
                is shell-split with ``shlex.split``.
            cwd: Working directory inside the sandbox.
            env: Per-exec env vars (in addition to the Session-level env
                injected at create time).

        Returns:
            A ``ModalSandboxProcess`` wrapping the live command handle.

        Raises:
            SandboxExecError: If Modal rejects the launch.
        """
        argv: List[str] = (
            command if isinstance(command, list) else shlex.split(command)
        )
        self._log_command(argv)

        kwargs: Dict[str, Any] = {}
        if cwd is not None:
            kwargs["workdir"] = cwd
        if env:
            kwargs["env"] = env
        started_at = time.time()
        try:
            process = self._sandbox.exec(*argv, **kwargs)
        except Exception as e:
            raise SandboxExecError(
                f"Modal exec failed to launch ({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxProcess(
            process, session=self, started_at=started_at
        )

    def _create_snapshot(self) -> SandboxSnapshot:
        """Capture the Sandbox's filesystem as a reusable Modal Image.

        Returns:
            A ``SandboxSnapshot`` whose ``ref`` is the Modal Image id. No
            in-memory process state is captured.
        """
        image = self._sandbox.snapshot_filesystem()
        return SandboxSnapshot(sandbox_id=self._parent.id, ref=image.object_id)

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a local file into the Sandbox.

        Args:
            local_path: Path to the file on the caller's machine.
            remote_path: Destination path inside the Sandbox.
        """
        self._sandbox.filesystem.copy_from_local(local_path, remote_path)

    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the Sandbox to local storage.

        Args:
            remote_path: Source path inside the Sandbox.
            local_path: Destination path on the caller's machine.
        """
        self._sandbox.filesystem.copy_to_local(remote_path, local_path)

    def _close(self) -> None:
        """No-op: the Modal Sandbox stays alive until destroy() or TTL."""

    def _destroy(self) -> None:
        """Terminate the Sandbox on Modal.

        A sandbox that has already exited (destroyed elsewhere or its TTL
        expired) is a successful no-op. Otherwise a termination failure
        propagates before the base `destroy()` template closes the handle,
        so on failure the handle stays open and destroy() can be retried.

        Raises:
            RuntimeError: If Modal fails to terminate a running sandbox.
        """
        # Already gone: nothing to terminate, and surfacing a Modal error
        # here would wrongly warn about a resource that is no longer
        # running or billing.
        if self._sandbox.poll() is not None:
            return
        try:
            self._sandbox.terminate()
        except Exception as e:
            raise RuntimeError(
                f"Failed to terminate Modal sandbox '{self.id}': {e}. "
                "It may keep running (and billing) until its TTL; retry "
                "destroy() or stop it from the Modal dashboard."
            ) from e


class ModalSandbox(BaseSandbox):
    """Sandbox flavor backed by Modal."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Modal sandbox component.

        Args:
            *args: Forwarded to ``StackComponent``.
            **kwargs: Forwarded to ``StackComponent``.
        """
        super().__init__(*args, **kwargs)
        # Explicit Modal client built lazily from the component's
        # credentials and reused across sessions; rebuilt if it closes.
        # The lock guards the build against concurrent create_session calls
        # (e.g. fanned-out mapped steps sharing this component instance).
        self._modal_client: Optional["modal.Client"] = None
        self._modal_client_lock = Lock()

    def _get_modal_client(self) -> Optional["modal.Client"]:
        """Return the explicit Modal client for this component, if any.

        Built once from the component's configured credentials and cached
        until it closes. Returns ``None`` when no credentials are set, so
        the Modal SDK falls back to its ambient authentication.

        Returns:
            The cached Modal client, or ``None`` for ambient auth.
        """
        if (
            self._modal_client is not None
            and not self._modal_client.is_closed()
        ):
            return self._modal_client
        with self._modal_client_lock:
            if (
                self._modal_client is not None
                and not self._modal_client.is_closed()
            ):
                return self._modal_client
            self._modal_client = (
                sandbox_utils.create_modal_client_from_credentials(
                    token_id=self.config.token_id,
                    token_secret=self.config.token_secret,
                )
            )
            return self._modal_client

    @property
    def config(self) -> ModalSandboxConfig:
        """Typed config.

        Returns:
            The component's Modal-specific config.
        """
        return cast(ModalSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class.

        Returns:
            ``ModalSandboxSettings``.
        """
        return ModalSandboxSettings

    def _registry_credentials(self, image: str) -> Optional[Tuple[str, str]]:
        """Return (username, password) for pulling the given image.

        The credentials of the active stack's container registry must only
        be handed to Modal when the image actually lives in that registry —
        the image is arbitrary user input (Docker Hub default), and leaking
        e.g. ECR credentials to a ``python:3.11-slim`` pull is unnecessary.

        Args:
            image: The image reference the sandbox will boot from.

        Returns:
            ``(username, password)`` when the image lives in the active
            stack's container registry and that registry exposes
            credentials, otherwise ``None`` (anonymous pull).
        """
        container_registry = Client().active_stack.container_registry
        if (
            container_registry
            and container_registry.is_valid_image_name_for_registry(image)
            and container_registry.credentials
        ):
            return container_registry.credentials
        return None

    def _build_create_kwargs(
        self,
        settings: ModalSandboxSettings,
        *,
        image: "modal.Image",
        modal_client: Optional["modal.Client"],
        environment: Dict[str, str],
    ) -> Dict[str, Any]:
        """Compose kwargs for ``modal.Sandbox.create`` via sandbox_utils.

        The Modal App is looked up per call (like the step operator does per
        submit) because ``modal_environment`` is a setting and may differ
        between sessions.

        Args:
            settings: The resolved sandbox settings.
            image: Modal Image to boot from.
            modal_client: Explicit Modal client (or ``None`` for ambient).
            environment: Env vars to inject into the new sandbox.

        Returns:
            Kwargs for ``modal.Sandbox.create``. The active step's
            ResourceSettings are NOT pulled in: the step's orchestrator
            already pays for cpu/memory/gpu; the sandbox would double them.
            Users size the sandbox via cpu/memory/gpu/region/cloud on
            ``ModalSandboxSettings`` directly.
        """
        environment_name = sandbox_utils.normalize_optional_config_value(
            settings.modal_environment
        )
        return sandbox_utils.build_sandbox_create_kwargs(
            app=sandbox_utils.lookup_modal_app(
                self.config.app_name,
                modal_environment=environment_name,
                modal_client=modal_client,
            ),
            image=image,
            settings=settings,
            resource_settings=ResourceSettings(
                cpu_count=settings.cpu, memory=settings.memory
            ),
            environment=environment,
            modal_client=modal_client,
        )

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Boot a fresh Modal Sandbox.

        Args:
            settings: Optional per-step overrides for image / env.

        Returns:
            A ``ModalSandboxSession`` wrapping the live Modal Sandbox.
        """
        settings = cast(ModalSandboxSettings, self.resolve_settings(settings))
        modal_client = self._get_modal_client()
        image = sandbox_utils.get_modal_image_from_registry(
            settings.image,
            registry_credentials=self._registry_credentials(settings.image),
        )
        sandbox = modal.Sandbox.create(
            **self._build_create_kwargs(
                settings,
                image=image,
                modal_client=modal_client,
                environment=self._resolve_session_environment(settings),
            )
        )
        return ModalSandboxSession(sandbox, parent=self)

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnect to a still-live Modal Sandbox by id.

        Args:
            session_id: The Modal sandbox object id (e.g. ``sb_xxx``).

        Returns:
            A ``ModalSandboxSession`` wrapping the existing live sandbox.

        Raises:
            RuntimeError: If Modal can't find a sandbox with the given id,
                or the sandbox has already terminated.
        """
        modal_client = self._get_modal_client()
        try:
            sandbox = sandbox_utils.get_sandbox_by_id(
                session_id, modal_client=modal_client
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to attach to Modal sandbox '{session_id}' "
                f"({type(e).__name__}): {e}"
            ) from e
        # Modal happily returns a handle for a dead sandbox; without this
        # check the first exec fails with a confusing Modal error.
        if sandbox.poll() is not None:
            raise RuntimeError(
                f"Modal sandbox '{session_id}' has already terminated "
                "(destroyed or TTL expired); create a new session instead."
            )
        return ModalSandboxSession(sandbox, parent=self)

    def restore(self, snapshot: SandboxSnapshot) -> SandboxSession:
        """Boot a new Session from a stored filesystem snapshot.

        Args:
            snapshot: A ``SandboxSnapshot`` whose ``ref`` is a Modal Image
                id captured via ``snapshot_filesystem()``.

        Returns:
            A new ``ModalSandboxSession`` initialized from the Image. No
            in-memory state from the original Session is preserved.

        Raises:
            RuntimeError: If Modal can't load the Image (e.g. id GC'd).
        """
        self._validate_snapshot(snapshot)
        settings = cast(ModalSandboxSettings, self.resolve_settings(None))
        modal_client = self._get_modal_client()
        try:
            image = modal.Image.from_id(snapshot.ref, client=modal_client)
            # Env vars are runtime config, not filesystem state, so the
            # snapshot image doesn't carry them — re-apply the resolved
            # session environment on restore.
            sandbox = modal.Sandbox.create(
                **self._build_create_kwargs(
                    settings,
                    image=image,
                    modal_client=modal_client,
                    environment=self._resolve_session_environment(settings),
                )
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to restore Modal sandbox from image "
                f"'{snapshot.ref}' ({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxSession(sandbox, parent=self)
