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
"""Docker daemon-backed sandbox: containerized sessions on a local Docker."""

import io
import posixpath
import tarfile
import threading
import time
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

import docker.errors
from docker.api.client import APIClient
from docker.client import DockerClient
from pydantic import Field

from zenml.logger import get_logger
from zenml.sandboxes.base import (
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)
from zenml.sandboxes.process import SandboxExecError, SandboxProcess
from zenml.sandboxes.session import SandboxSession
from zenml.sandboxes.snapshot import SandboxSnapshot

if TYPE_CHECKING:
    from docker.models.containers import Container

logger = get_logger(__name__)

DOCKER_SANDBOX_FLAVOR = "docker"

# Label used to find sessions created by this component, so `attach()`
# and janitorial tooling can distinguish them from unrelated containers.
_SESSION_LABEL = "zenml-sandbox-session"

# Keep-alive entrypoint. The image's own ENTRYPOINT is cleared so images
# that define one (e.g. task images with their own CMD/ENTRYPOINT) still
# start the keep-alive instead of exiting immediately.
_KEEPALIVE_COMMAND = ["sleep", "infinity"]


class DockerSandboxSettings(BaseSandboxSettings):
    """Docker sandbox settings."""

    image: str = Field(
        default="python:3.11-slim",
        description="Container image sessions boot from. Task-level image "
        "overrides (e.g. Harbor's docker_image) replace this per session.",
    )
    workdir: str = Field(
        default="/workspace",
        description="Working directory inside the container. Relative "
        "exec/upload/download paths resolve against it.",
    )
    cpu_limit: Optional[float] = Field(
        default=None,
        description="CPU cores the container may use (Docker --cpus). "
        "Unlimited if unset.",
    )
    memory_limit: Optional[str] = Field(
        default=None,
        description="Memory limit for the container in Docker's byte-unit "
        "syntax, e.g. '2g'. Unlimited if unset.",
    )
    pull_policy: str = Field(
        default="missing",
        description="When to pull the session image: 'always' pulls on "
        "every session, 'missing' only when the image is not present "
        "locally, 'never' never pulls.",
    )


class DockerSandboxConfig(BaseSandboxConfig, DockerSandboxSettings):
    """Docker sandbox configuration."""

    @property
    def is_local(self) -> bool:
        """Whether this sandbox component is running locally.

        Returns:
            True: sessions run on the host's Docker daemon.
        """
        return True


class DockerSandboxProcess(SandboxProcess):
    """Handle to a command running in a Docker sandbox session."""

    def __init__(
        self,
        *,
        client: APIClient,
        exec_id: str,
        session: "DockerSandboxSession",
        started_at: float,
    ) -> None:
        """Initialize the Docker sandbox process.

        Args:
            client: Low-level Docker API client.
            exec_id: The Docker exec instance id.
            session: The owning session.
            started_at: The wall-clock time the process started.
        """
        super().__init__(session=session, started_at=started_at)
        self._client = client
        self._exec_id = exec_id
        # Docker multiplexes both streams over one connection, so a single
        # reader thread demuxes into per-stream line buffers that the
        # stdout()/stderr() iterators consume concurrently (collect()
        # drains both in parallel threads).
        self._stdout_lines: List[str] = []
        self._stderr_lines: List[str] = []
        self._buffers_done = threading.Event()
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()

    def _drain(self) -> None:
        """Demux the exec output stream into per-stream line buffers."""
        stdout_tail = b""
        stderr_tail = b""
        try:
            stream = self._client.exec_start(
                self._exec_id, stream=True, demux=True
            )
            for stdout_chunk, stderr_chunk in stream:
                if stdout_chunk:
                    stdout_tail = self._append_lines(
                        stdout_tail + stdout_chunk, self._stdout_lines
                    )
                if stderr_chunk:
                    stderr_tail = self._append_lines(
                        stderr_tail + stderr_chunk, self._stderr_lines
                    )
        except Exception:
            logger.debug(
                "Docker sandbox exec stream ended abnormally", exc_info=True
            )
        finally:
            if stdout_tail:
                self._stdout_lines.append(stdout_tail.decode(errors="replace"))
            if stderr_tail:
                self._stderr_lines.append(stderr_tail.decode(errors="replace"))
            self._buffers_done.set()

    @staticmethod
    def _append_lines(data: bytes, target: List[str]) -> bytes:
        """Split a chunk into complete lines, appending them to a buffer.

        Args:
            data: Accumulated bytes (previous tail + new chunk).
            target: The line buffer to append complete lines to.

        Returns:
            The trailing incomplete line, carried into the next chunk.
        """
        lines = data.splitlines(keepends=True)
        if lines and not lines[-1].endswith(b"\n"):
            tail = lines.pop()
        else:
            tail = b""
        target.extend(line.decode(errors="replace") for line in lines)
        return tail

    def _iter_buffer(self, buffer: List[str]) -> Iterator[str]:
        """Yield lines from a buffer until the process output ends.

        Args:
            buffer: The line buffer fed by the reader thread.

        Yields:
            Output lines.
        """
        index = 0
        while True:
            while index < len(buffer):
                yield buffer[index]
                index += 1
            if self._buffers_done.is_set() and index >= len(buffer):
                return
            time.sleep(0.01)

    def stdout(self) -> Iterator[str]:
        """Yield stdout lines.

        Returns:
            An iterator over standard output lines.
        """
        return self._iter_buffer(self._stdout_lines)

    def stderr(self) -> Iterator[str]:
        """Yield stderr lines.

        Returns:
            An iterator over standard error lines.
        """
        return self._iter_buffer(self._stderr_lines)

    def wait(self, timeout: Optional[float] = None) -> int:
        """Block until the command exits.

        Args:
            timeout: Timeout in seconds to wait.

        Raises:
            TimeoutError: If the command does not exit within the timeout.

        Returns:
            The exit code.
        """
        deadline = None if timeout is None else time.time() + timeout
        self._reader.join(timeout=timeout)
        while True:
            code = self.exit_code
            if code is not None:
                return code
            if deadline is not None and time.time() > deadline:
                raise TimeoutError(
                    "Timed out waiting for Docker sandbox command to exit."
                )
            time.sleep(0.05)

    def kill(self) -> None:
        """Terminate the command.

        Docker has no API to kill a single exec instance, so this kills
        the exec's process tree inside the container by PID.
        """
        try:
            pid = self._client.exec_inspect(self._exec_id).get("Pid")
            if pid:
                container_id = self._client.exec_inspect(self._exec_id)[
                    "ContainerID"
                ]
                killer = self._client.exec_create(
                    container_id, ["kill", "-9", str(pid)]
                )
                self._client.exec_start(killer["Id"])
        except Exception:
            logger.debug(
                "Failed to kill Docker sandbox exec process", exc_info=True
            )

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code, or `None` if the command is still running.

        Returns:
            The exit code, or `None` while running.
        """
        try:
            inspection = self._client.exec_inspect(self._exec_id)
        except Exception:
            logger.debug(
                "Failed to inspect Docker sandbox exec", exc_info=True
            )
            return None
        if inspection.get("Running"):
            return None
        return cast(Optional[int], inspection.get("ExitCode"))


class DockerSandboxSession(SandboxSession):
    """Docker sandbox session backed by one container."""

    def __init__(
        self,
        *,
        container: "Container",
        workdir: str,
        env: Dict[str, str],
        parent: "DockerSandbox",
        destroy_on_exit: bool = False,
        id: Optional[str] = None,
    ) -> None:
        """Initialize the Docker sandbox session.

        Args:
            container: The running container backing this session.
            workdir: Working directory inside the container.
            env: Environment variables injected into every exec.
            parent: The sandbox component that created this session.
            destroy_on_exit: Whether to destroy the sandbox session when the
                session context manager exits.
            id: Session id override (used by `attach()` to keep the
                original id).
        """
        self._container = container
        self._workdir = workdir
        self._env = env
        super().__init__(
            id=id or f"docker-{uuid.uuid4().hex[:12]}",
            parent=parent,
            destroy_on_exit=destroy_on_exit,
        )

    def _remote_path(self, path: str) -> str:
        """Resolve a container path against the session workdir.

        Args:
            path: Absolute container path, or a path relative to the
                session workdir.

        Returns:
            An absolute container path.
        """
        if posixpath.isabs(path):
            return path
        return posixpath.join(self._workdir, path)

    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Execute a command inside the session container.

        Args:
            command: The command to execute.
            cwd: Optional working directory override; relative paths
                resolve against the session workdir.
            env: Environment variables to set for the command.

        Raises:
            SandboxExecError: If the exec instance fails to launch.

        Returns:
            Process handle.
        """
        self._log_command(command)
        merged_env = {**self._env, **(env or {})}
        workdir = self._remote_path(cwd) if cwd else self._workdir
        api = self._container.client.api
        started_at = time.time()
        try:
            exec_instance = api.exec_create(
                self._container.id,
                command,
                environment=merged_env,
                workdir=workdir,
            )
        except Exception as e:
            raise SandboxExecError(
                f"Docker sandbox execution failed to launch: {e}"
            ) from e
        return DockerSandboxProcess(
            client=api,
            exec_id=exec_instance["Id"],
            session=self,
            started_at=started_at,
        )

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file into the session container.

        Args:
            local_path: Source path on the caller's filesystem.
            remote_path: Destination path in the container; relative
                paths resolve against the session workdir.
        """
        destination = self._remote_path(remote_path)
        directory = posixpath.dirname(destination) or "/"
        # put_archive requires an existing destination directory.
        mkdir = self._container.client.api.exec_create(
            self._container.id, ["mkdir", "-p", directory]
        )
        self._container.client.api.exec_start(mkdir["Id"])
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            tar.add(local_path, arcname=posixpath.basename(destination))
        buffer.seek(0)
        self._container.put_archive(directory, buffer.getvalue())

    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the session container.

        Args:
            remote_path: Source path in the container; relative paths
                resolve against the session workdir.
            local_path: Destination path on the caller's filesystem.

        Raises:
            FileNotFoundError: If the remote file does not exist or is
                not a regular file.
        """
        source = self._remote_path(remote_path)
        stream, _ = self._container.get_archive(source)
        buffer = io.BytesIO()
        for chunk in stream:
            buffer.write(chunk)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer) as tar:
            member_name = posixpath.basename(source)
            try:
                extracted = tar.extractfile(member_name)
            except KeyError:
                extracted = None
            if extracted is None:
                raise FileNotFoundError(
                    f"'{remote_path}' is not a regular file in the sandbox."
                )
            with open(local_path, "wb") as destination_file:
                destination_file.write(extracted.read())

    def _create_snapshot(self) -> SandboxSnapshot:
        """Snapshot the container filesystem as a local image.

        Returns:
            A snapshot whose ref is the committed Docker image id.
        """
        image = self._container.commit(
            repository="zenml-sandbox-snapshot",
            tag=f"{self.id}-{uuid.uuid4().hex[:8]}",
        )
        return SandboxSnapshot(
            sandbox_id=self._parent.id,
            ref=image.id,
            metadata={
                "session_id": self.id,
                "tags": list(image.tags),
            },
        )

    def _close(self) -> None:
        """Close the session handle; the container keeps running.

        Mirrors the remote-flavor contract: `close()` releases the handle
        only, `destroy()` removes the container.
        """

    def _destroy(self) -> None:
        """Force-remove the session container."""
        self._container.remove(force=True)


class DockerSandbox(BaseSandbox):
    """Sandbox flavor backed by the local Docker daemon.

    Sessions are containers running a keep-alive command; `exec`, file
    transfer, and snapshots map onto Docker exec, archive copy, and
    commit. This is the container-isolated local counterpart to the
    `local` (host subprocess) flavor.
    """

    _docker_client: Optional[DockerClient] = None

    @property
    def config(self) -> DockerSandboxConfig:
        """Docker sandbox configuration.

        Returns:
            The Docker sandbox configuration.
        """
        return cast(DockerSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type[BaseSandboxSettings]]:
        """Settings class.

        Returns:
            `DockerSandboxSettings`.
        """
        return DockerSandboxSettings

    def image_settings(self, image: str) -> Optional[BaseSandboxSettings]:
        """Build a settings override that pins the container image.

        Args:
            image: The container image reference to pin.

        Returns:
            Docker sandbox settings carrying the image.
        """
        return DockerSandboxSettings(image=image)

    def _get_client(self) -> DockerClient:
        """Build (once) and return the Docker client.

        Returns:
            The Docker SDK client.

        Raises:
            RuntimeError: If no Docker daemon is reachable.
        """
        if self._docker_client is None:
            try:
                self._docker_client = DockerClient.from_env()
                self._docker_client.ping()
            except Exception as e:
                self._docker_client = None
                raise RuntimeError(
                    "The Docker sandbox requires a reachable Docker "
                    f"daemon: {e}"
                ) from e
        return self._docker_client

    def _ensure_image(
        self, client: DockerClient, settings: DockerSandboxSettings
    ) -> None:
        """Make sure the session image is available per the pull policy.

        Args:
            client: The Docker client.
            settings: The resolved session settings.

        Raises:
            RuntimeError: If the image is missing and the pull policy
                forbids pulling it.
        """
        if settings.pull_policy == "always":
            client.images.pull(settings.image)
            return
        try:
            client.images.get(settings.image)
        except docker.errors.ImageNotFound:
            if settings.pull_policy == "never":
                raise RuntimeError(
                    f"Image '{settings.image}' is not present locally and "
                    "the pull policy is 'never'."
                )
            logger.info("Pulling sandbox image '%s'...", settings.image)
            client.images.pull(settings.image)

    def create_session(
        self,
        settings: Optional[BaseSandboxSettings] = None,
        destroy_on_exit: bool = False,
    ) -> SandboxSession:
        """Create a fresh container-backed sandbox session.

        Args:
            settings: Optional settings overrides.
            destroy_on_exit: Whether to destroy the sandbox session when the
                session context manager exits.

        Returns:
            A Docker sandbox session.
        """
        settings = cast(DockerSandboxSettings, self.resolve_settings(settings))
        client = self._get_client()
        self._ensure_image(client, settings)
        env = self._resolve_session_environment(settings)
        session_id = f"docker-{uuid.uuid4().hex[:12]}"

        run_kwargs: Dict[str, Any] = {
            "detach": True,
            "name": f"zenml-sandbox-{session_id}",
            "labels": {_SESSION_LABEL: session_id},
            "working_dir": settings.workdir,
            "entrypoint": [],
        }
        if settings.cpu_limit is not None:
            run_kwargs["nano_cpus"] = int(settings.cpu_limit * 1e9)
        if settings.memory_limit is not None:
            run_kwargs["mem_limit"] = settings.memory_limit

        container = client.containers.run(
            settings.image, _KEEPALIVE_COMMAND, **run_kwargs
        )
        # The workdir may not exist in arbitrary task images.
        mkdir = client.api.exec_create(
            container.id, ["mkdir", "-p", settings.workdir]
        )
        client.api.exec_start(mkdir["Id"])

        return DockerSandboxSession(
            container=container,
            workdir=settings.workdir,
            env=env,
            parent=self,
            destroy_on_exit=destroy_on_exit,
            id=session_id,
        )

    def attach(self, session_id: str) -> SandboxSession:
        """Attach to a running Docker sandbox session.

        Args:
            session_id: The ID of the running sandbox session.

        Raises:
            KeyError: If no running session container carries the id.

        Returns:
            Sandbox session.
        """
        client = self._get_client()
        containers = client.containers.list(
            filters={"label": f"{_SESSION_LABEL}={session_id}"}
        )
        if not containers:
            raise KeyError(
                f"No running Docker sandbox session '{session_id}' found."
            )
        settings = cast(DockerSandboxSettings, self.resolve_settings(None))
        return DockerSandboxSession(
            container=containers[0],
            workdir=settings.workdir,
            env=self._resolve_session_environment(settings),
            parent=self,
            id=session_id,
        )

    def restore(self, snapshot: SandboxSnapshot) -> SandboxSession:
        """Restore a session from a committed snapshot image.

        Args:
            snapshot: The snapshot to restore from.

        Returns:
            A new session booted from the snapshot image.
        """
        self._validate_snapshot(snapshot)
        return self.create_session(
            settings=DockerSandboxSettings(image=snapshot.ref)
        )


class DockerSandboxFlavor(BaseSandboxFlavor):
    """Docker daemon sandbox flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            The flavor name.
        """
        return DOCKER_SANDBOX_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """Docs URL.

        Returns:
            The docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """SDK docs URL.

        Returns:
            The flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """Dashboard logo URL.

        Returns:
            The flavor logo URL.
        """
        return (
            "https://public-flavor-logos.s3.eu-central-1.amazonaws.com"
            "/orchestrator/docker.png"
        )

    @property
    def config_class(self) -> Type[DockerSandboxConfig]:
        """Config class.

        Returns:
            `DockerSandboxConfig`.
        """
        return DockerSandboxConfig

    @property
    def implementation_class(self) -> Type[DockerSandbox]:
        """Implementation class.

        Returns:
            `DockerSandbox`.
        """
        return DockerSandbox
