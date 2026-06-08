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
import math
import shlex
import threading
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal.flavors import (
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxSettings,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
    SandboxSnapshot,
)

# Sentinel for "use the active step's containerized-orchestrator image."
# Inlined here so the image-resolution behavior stays owned by this flavor
# and the base stays minimal.
MODAL_STEP_IMAGE_SENTINEL = "<step>"

if TYPE_CHECKING:
    import modal  # noqa: F401

    from zenml.config import ResourceSettings

logger = get_logger(__name__)


def _normalize_optional_config_value(value: Optional[str]) -> Optional[str]:
    """Strip whitespace and return None for empty strings.

    Args:
        value: The raw config value.

    Returns:
        Stripped non-empty string, or ``None``.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _line_buffer(chunks: Iterable[Any]) -> Iterator[str]:
    """Re-emit byte/str chunks one decoded line at a time.

    Args:
        chunks: Source iterable yielding bytes, str, or None.

    Yields:
        Lines with trailing newline when present; a final newline-less
        remainder is yielded once the source is exhausted.
    """
    # Mirrors the SandboxProcess.stdout() / stderr() contract (line-delimited
    # utf-8). Modal returns LogsReader iterables that yield byte chunks, not
    # lines, so we line-buffer on this side.
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
            _line_buffer(self._process.stdout), log_level=logging.INFO
        )

    def stderr(self) -> Iterator[str]:
        """Returns a line-buffered, log-wrapped stderr iterator.

        Returns:
            Line iterator wrapped via ``session._wrap_stream``.
        """
        return self._session._wrap_stream(
            _line_buffer(self._process.stderr), log_level=logging.ERROR
        )

    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the command exits.

        Args:
            timeout: Not supported by Modal's ``ContainerProcess.wait()``.
                Use the Session-level ``timeout`` setting to bound total
                Session lifetime.

        Returns:
            The exit code.

        Raises:
            NotImplementedError: If ``timeout`` is not ``None``.
        """
        if timeout is not None:
            raise NotImplementedError(
                "Modal does not support per-exec timeouts. Use "
                "ModalSandboxSettings.timeout for Session-level TTL, or "
                "wrap the wait call in your own watchdog."
            )
        self._process.wait()
        return int(self._process.returncode or 0)

    def kill(self) -> None:
        """Best-effort process termination."""
        # Modal's ContainerProcess does not expose a per-command kill —
        # only wait / poll / stdin / stdout / stderr / attach. Closing
        # stdin signals EOF, which lets well-behaved processes exit. For
        # a hard kill, call ModalSandboxSession.destroy().
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
        self._parent_modal = parent
        super().__init__(id=sandbox.object_id, parent=parent)

    def _get_dashboard_url(self) -> Optional[str]:
        """Returns the Modal sandbox's dashboard URL, or ``None``.

        Returns:
            URL string from ``Sandbox.get_dashboard_url()`` — older Modal
            SDKs without this API return ``None``.
        """
        try:
            url = self._sandbox.get_dashboard_url()
        except Exception as e:  # noqa: BLE001
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
            list(command)
            if isinstance(command, list)
            else shlex.split(command)
        )
        self._log_command(argv)

        kwargs: Dict[str, Any] = {}
        if cwd is not None:
            kwargs["workdir"] = cwd
        if env:
            # Modal 1.x validated env= on Sandbox.create (strickvl PR
            # #4038) but not on ContainerProcess.exec. Stick with the
            # secrets= path on per-exec env injection until that's
            # verified end-to-end against a live Modal 1.x runtime.
            import modal

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
        return ModalSandboxProcess(
            process, session=self, started_at=started_at
        )

    def create_snapshot(self) -> SandboxSnapshot:
        """Capture the Sandbox's filesystem as a reusable Modal Image.

        Returns:
            A ``SandboxSnapshot`` whose ``ref`` is the Modal Image id. No
            in-memory process state is captured.
        """
        image = self._sandbox.snapshot_filesystem()
        return SandboxSnapshot(
            sandbox_id=self._parent_modal.id, ref=image.object_id
        )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a local file into the Sandbox.

        Args:
            local_path: Path to the file on the caller's machine.
            remote_path: Destination path inside the Sandbox.
        """
        # Uses Modal's Sandbox.filesystem.copy_from_local() API; the
        # older Sandbox.open() + FileIO.write() path is deprecated by
        # Modal as of 2026-03-09.
        self._sandbox.filesystem.copy_from_local(local_path, remote_path)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the Sandbox to local storage.

        Args:
            remote_path: Source path inside the Sandbox.
            local_path: Destination path on the caller's machine.
        """
        # Uses Modal's Sandbox.filesystem.copy_to_local() API; the older
        # Sandbox.open() + FileIO.read() path is deprecated by Modal as
        # of 2026-03-09.
        self._sandbox.filesystem.copy_to_local(remote_path, local_path)

    def close(self) -> None:
        """No-op: Modal ``Sandbox`` has no client-side resources to drop."""
        # The Sandbox keeps running on Modal until its TTL expires; use
        # destroy() to force-stop immediately. Logging-context teardown
        # is centralized in base SandboxSession.__exit__.

    def destroy(self) -> None:
        """Terminate the Sandbox on Modal."""
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


def _resolve_step_image() -> Optional[str]:
    """Look up the active step's containerized-orchestrator image.

    Returns:
        The image URI for the active step's build, or ``None`` if no step
        context is active, the run carries no snapshot, or the snapshot
        was assembled without a Docker build.
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
        logger.debug("Step image lookup for Modal sandbox failed: %s", e)
        return None


def _resolve_image(
    base_image: Optional[str],
    default_image: str,
    registry_secret: Optional[Any] = None,
) -> "modal.Image":
    """Resolve a base_image setting into a concrete Modal Image.

    Args:
        base_image: The setting value — ``None``, the module-local
            ``MODAL_STEP_IMAGE_SENTINEL``, or a registry URI.
        default_image: Fallback image URI from the component config.
        registry_secret: Optional ``modal.Secret`` carrying registry
            credentials; passed through to ``Image.from_registry``.

    Returns:
        A ``modal.Image`` instance ready to pass to ``Sandbox.create``.
    """
    import modal

    def _from_registry(image_uri: str) -> "modal.Image":
        if registry_secret is not None:
            return modal.Image.from_registry(image_uri, secret=registry_secret)
        return modal.Image.from_registry(image_uri)

    if base_image is None:
        return _from_registry(default_image)
    if base_image == MODAL_STEP_IMAGE_SENTINEL:
        step_image = _resolve_step_image()
        if not step_image:
            logger.warning(
                "Step-image sentinel requested but the current step is "
                "not running on a containerized orchestrator with a "
                "built image; falling back to the flavor's default "
                "image '%s'.",
                default_image,
            )
            return _from_registry(default_image)
        return _from_registry(step_image)
    return _from_registry(base_image)


class ModalSandbox(BaseSandbox):
    """Sandbox flavor backed by Modal."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Modal sandbox component.

        Args:
            *args: Forwarded to ``StackComponent``.
            **kwargs: Forwarded to ``StackComponent``.
        """
        super().__init__(*args, **kwargs)
        # Modal App lookup is a network round-trip; cache after the first
        # create_session / restore call.
        self._app: Optional[Any] = None
        # Lazy thread-safe Modal client cache, recreated when closed.
        self._modal_client: Optional[Any] = None
        self._modal_client_lock = threading.Lock()

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

    def _get_modal_client(self) -> Optional[Any]:
        """Return an explicit Modal client when credentials are configured.

        Returns:
            A modal.Client built from token_id / token_secret, or None
            when no credentials are configured (Modal then uses its
            ambient auth). The both-or-neither precondition is enforced
            upstream by ModalStepOperatorConfig's validator.
        """
        token_id = _normalize_optional_config_value(self.config.token_id)
        token_secret = _normalize_optional_config_value(
            self.config.token_secret
        )
        if not token_id or not token_secret:
            return None

        import modal

        with self._modal_client_lock:
            client = self._modal_client
            if client is None or client.is_closed():
                client = modal.Client.from_credentials(token_id, token_secret)
                self._modal_client = client

        return client

    def _get_app(
        self,
        environment_name: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> Any:
        """Return this component's Modal ``App``, caching the lookup.

        Args:
            environment_name: Modal environment to look the app up in.
            client: Explicit Modal client; ``None`` falls back to ambient.

        Returns:
            The Modal App.
        """
        if self._app is None:
            import modal

            self._app = modal.App.lookup(
                self.config.app_name,
                create_if_missing=True,
                environment_name=environment_name,
                client=client,
            )
        return self._app

    def _registry_secret(self) -> Optional[Any]:
        """Return a Modal Secret holding container-registry creds, if any.

        Returns:
            A ``modal.Secret`` when the stack's container registry exposes
            credentials, otherwise ``None`` (anonymous pull).
        """
        try:
            container_registry = self.stack.container_registry
        except Exception:
            container_registry = None
        if container_registry is None:
            return None
        creds = container_registry.credentials
        if not creds:
            return None

        import modal

        username, password = creds
        return modal.Secret.from_dict(
            {"REGISTRY_USERNAME": username, "REGISTRY_PASSWORD": password}
        )

    def _modal_sandbox_kwargs(
        self,
        eff: ModalSandboxSettings,
        *,
        client: Optional[Any],
        with_env: bool = True,
    ) -> Dict[str, Any]:
        """Build the kwargs passed to ``modal.Sandbox.create``.

        Args:
            eff: Effective per-step settings.
            client: Explicit Modal client (or ``None`` for ambient auth).
            with_env: If True, the resolved Session env is exported as
                ``env=`` on ``Sandbox.create``. Skipped on the restore
                path where injecting env into a frozen filesystem image
                is rarely what the caller wants.

        Returns:
            Kwargs for ``modal.Sandbox.create``.
        """
        from zenml.config.resource_settings import ByteUnit
        from zenml.integrations.modal.step_operators.modal_step_operator import (
            get_gpu_values,
        )

        resource_settings = self._active_resource_settings()
        memory_mb = resource_settings.get_memory(ByteUnit.MB)
        # ModalSandboxSettings inherits from ModalStepOperatorSettings, so
        # get_gpu_values accepts it directly — single source of truth for
        # the "<type>:<count>" composition shared with the step operator.
        gpu_values = get_gpu_values(eff, resource_settings)

        environment_name = _normalize_optional_config_value(
            getattr(eff, "modal_environment", None)
        )

        kwargs: Dict[str, Any] = {
            "app": self._get_app(
                environment_name=environment_name, client=client
            )
        }
        if client is not None:
            kwargs["client"] = client
        if with_env:
            env = self._resolve_session_environment(eff)
            if env:
                # Modal 1.x: pass runtime env via env= (not via secrets=).
                # Keeps the Image build cache clean of per-step values.
                kwargs["env"] = env
        # `timeout` is inherited from ModalStepOperatorSettings (validated
        # ge=1, le=86400). Single source of truth shared with the step
        # operator — one timeout knob per stack.
        kwargs["timeout"] = eff.timeout
        if gpu_values is not None:
            kwargs["gpu"] = gpu_values
        if resource_settings.cpu_count is not None:
            kwargs["cpu"] = resource_settings.cpu_count
        if memory_mb is not None:
            # Round up: Modal rejects fractional MB; truncating could
            # under-provision a tight memory request.
            kwargs["memory"] = math.ceil(memory_mb)
        if eff.region is not None:
            kwargs["region"] = eff.region
        if eff.cloud is not None:
            kwargs["cloud"] = eff.cloud
        return kwargs

    @staticmethod
    def _active_resource_settings() -> "ResourceSettings":
        """Return the active step's ``ResourceSettings``, or defaults.

        Returns:
            The step's resource settings (cpu_count, memory, gpu_count).
        """
        # When no step context is available (ad-hoc usage from a script)
        # we fall back to empty settings so kwargs composition still works.
        from zenml.config import ResourceSettings
        from zenml.steps.step_context import StepContext

        ctx = StepContext.get()
        if ctx is None:
            return ResourceSettings()
        return ctx.step_run.config.resource_settings

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Boot a fresh Modal Sandbox.

        Args:
            settings: Optional per-step overrides for image / resources / env.

        Returns:
            A ``ModalSandboxSession`` wrapping the live Modal Sandbox.
        """
        import modal

        eff = cast(ModalSandboxSettings, self.resolve_settings(settings))
        client = self._get_modal_client()
        image = _resolve_image(
            eff.base_image,
            self.config.default_image,
            registry_secret=self._registry_secret(),
        )

        sandbox = modal.Sandbox.create(
            image=image,
            **self._modal_sandbox_kwargs(eff, client=client),
        )
        return ModalSandboxSession(sandbox, parent=self)

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnect to a still-live Modal Sandbox by id.

        Args:
            session_id: The Modal sandbox object id (e.g. ``sb_xxx``).

        Returns:
            A ``ModalSandboxSession`` wrapping the existing live sandbox.

        Raises:
            RuntimeError: If Modal can't find a sandbox with the given id.
        """
        import modal

        client = self._get_modal_client()
        try:
            if client is not None:
                sandbox = modal.Sandbox.from_id(session_id, client=client)
            else:
                sandbox = modal.Sandbox.from_id(session_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to attach to Modal sandbox '{session_id}' "
                f"({type(e).__name__}): {e}"
            ) from e
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
        # Env injection is skipped: a restored sandbox boots from a frozen
        # Image and the caller almost never wants to layer a fresh env
        # merge on top.
        import modal

        eff = cast(ModalSandboxSettings, self.resolve_settings(None))
        client = self._get_modal_client()
        try:
            image = modal.Image.from_id(snapshot.ref)
            sandbox = modal.Sandbox.create(
                image=image,
                **self._modal_sandbox_kwargs(
                    eff, client=client, with_env=False
                ),
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to restore Modal sandbox from image "
                f"'{snapshot.ref}' ({type(e).__name__}): {e}"
            ) from e
        return ModalSandboxSession(sandbox, parent=self)
