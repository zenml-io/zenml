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
"""Docker sandbox flavor."""

import copy
import io
import logging
import posixpath
import queue
import shlex
import shutil
import tarfile
import threading
import time
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
from uuid import uuid4

from docker.api.client import APIClient
from docker.client import DockerClient
from docker.errors import ImageNotFound, NotFound
from pydantic import Field

from zenml.container_engines import (
    DockerContainerEngine,
    get_container_engine,
)
from zenml.enums import ContainerEngineType
from zenml.logger import get_logger
from zenml.sandboxes.base import (
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
    ContainerizedSandboxSettings,
)
from zenml.sandboxes.process import SandboxExecError, SandboxProcess
from zenml.sandboxes.session import SandboxSession
from zenml.sandboxes.snapshot import SandboxSnapshot
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from docker.models.containers import Container

logger = get_logger(__name__)

DOCKER_SANDBOX_FLAVOR = "docker"


_SESSION_ID_LABEL = "zenml-sandbox-session"
_SNAPSHOT_REPOSITORY = "zenml-sandbox-snapshot"

# Docker has no API to terminate an exec instance and `exec_inspect`
# reports a host-namespace pid that is meaningless inside the container.
# Every command therefore runs through this wrapper, which records the
# container-namespace pid to a file that `kill()` reads.
_PID_FILE_WRAPPER = 'echo "$$" >"$1" && shift && exec "$@"'

_STREAM_END = object()


def _split_lines_with_buffer(
    chunk: bytes, buffer: bytes
) -> Tuple[List[str], bytes]:
    """Split a chunk into lines and remaining buffer.

    Args:
        chunk: A chunk from a stream.
        buffer: The remaining buffer from previous chunks.

    Returns:
        A tuple of decoded lines and remaining buffer.
    """
    combined = buffer + chunk
    lines = combined.splitlines(keepends=True)
    if lines and not lines[-1].endswith(b"\n"):
        buffer = lines.pop()
    else:
        buffer = b""

    return [line.decode(errors="replace") for line in lines], buffer


class DockerSandboxPullPolicy(StrEnum):
    """Docker sandbox image pull policy."""

    ALWAYS = "always"
    MISSING = "missing"
    NEVER = "never"


class DockerSandboxSettings(ContainerizedSandboxSettings):
    """Docker sandbox settings."""

    workdir: str = Field(
        default="/workspace",
        description="Working directory inside the session container.",
    )
    cpu_limit: Optional[float] = Field(
        default=None,
        description="Number of CPU cores a session container may use. "
        "Unlimited if unset.",
    )
    memory_limit: Optional[str] = Field(
        default=None,
        description="Memory limit for a session container in Docker "
        "byte-unit syntax such as '2g'. Unlimited if unset.",
    )
    pull_policy: DockerSandboxPullPolicy = Field(
        default=DockerSandboxPullPolicy.MISSING,
        description="When to pull the session image.",
    )
    run_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional arguments to pass to the `docker run` call "
        "that starts a session container. (See "
        "https://docker-py.readthedocs.io/en/stable/containers.html for a "
        "list of what can be passed)",
    )


class DockerSandboxConfig(BaseSandboxConfig, DockerSandboxSettings):
    """Docker sandbox configuration."""

    @property
    def is_local(self) -> bool:
        """Whether this sandbox component is running locally.

        Returns:
            Whether this sandbox component is running locally.
        """
        return True


class DockerSandboxProcess(SandboxProcess):
    """Docker sandbox process wrapping an exec instance."""

    def __init__(
        self,
        client: APIClient,
        container_id: str,
        exec_id: str,
        pid_file: str,
        session: "DockerSandboxSession",
        started_at: float,
    ) -> None:
        """Initialize the Docker sandbox process.

        Args:
            client: Low-level Docker API client.
            container_id: ID of the container the command runs in.
            exec_id: ID of the exec instance running the command.
            pid_file: Path of the file inside the container that the
                command pid was recorded to.
            session: The owning session.
            started_at: The wall-clock time the process started.
        """
        super().__init__(session=session, started_at=started_at)
        self._client = client
        self._container_id = container_id
        self._exec_id = exec_id
        self._pid_file = pid_file
        self._exit_code: Optional[int] = None
        self._stdout_queue: "queue.Queue[object]" = queue.Queue()
        self._stderr_queue: "queue.Queue[object]" = queue.Queue()
        self._done = threading.Event()
        self._drain_thread = threading.Thread(target=self._drain, daemon=True)
        self._drain_thread.start()

    def _drain(self) -> None:
        """Drain the exec output stream into the per-stream line queues."""
        stdout_buffer = b""
        stderr_buffer = b""
        try:
            stream = self._client.exec_start(
                self._exec_id, stream=True, demux=True
            )
            for stdout_chunk, stderr_chunk in stream:
                if stdout_chunk:
                    lines, stdout_buffer = _split_lines_with_buffer(
                        chunk=stdout_chunk, buffer=stdout_buffer
                    )
                    for line in lines:
                        self._stdout_queue.put(line)
                if stderr_chunk:
                    lines, stderr_buffer = _split_lines_with_buffer(
                        chunk=stderr_chunk, buffer=stderr_buffer
                    )
                    for line in lines:
                        self._stderr_queue.put(line)
        except Exception as e:
            logger.debug("Error while draining Docker sandbox streams: %s", e)
            self._stderr_queue.put(f"Docker sandbox stream failed: {e}\n")
        finally:
            if stdout_buffer:
                self._stdout_queue.put(stdout_buffer.decode(errors="replace"))
            if stderr_buffer:
                self._stderr_queue.put(stderr_buffer.decode(errors="replace"))
            self._exit_code = self._read_exit_code()
            self._stdout_queue.put(_STREAM_END)
            self._stderr_queue.put(_STREAM_END)
            self._done.set()

    def _read_exit_code(self) -> int:
        """Read the exit code once the output stream has ended.

        Returns:
            The exit code.
        """
        try:
            # The exec can be reported as running for a moment after its
            # stream ends.
            while True:
                inspection = self._client.exec_inspect(self._exec_id)
                if not inspection.get("Running"):
                    exit_code = inspection.get("ExitCode")
                    return 1 if exit_code is None else int(exit_code)

                time.sleep(0.05)
        except Exception as e:
            logger.debug("Failed to inspect Docker sandbox exec: %s", e)
            return 1

    @staticmethod
    def _iter_queue(q: "queue.Queue[object]") -> Iterator[str]:
        """Iterate queue items until the sentinel is reached.

        Args:
            q: Queue of stream line items.

        Yields:
            Stream lines.
        """
        while True:
            item = q.get()
            if item is _STREAM_END:
                break

            yield cast(str, item)

    def stdout(self) -> Iterator[str]:
        """Stdout line iterator.

        Returns:
            Stdout line iterator.
        """
        return self._session._wrap_stream(
            self._iter_queue(self._stdout_queue), log_level=logging.INFO
        )

    def stderr(self) -> Iterator[str]:
        """Stderr line iterator.

        Returns:
            Stderr line iterator.
        """
        return self._session._wrap_stream(
            self._iter_queue(self._stderr_queue), log_level=logging.ERROR
        )

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for command completion.

        Args:
            timeout: Timeout in seconds to wait.

        Raises:
            TimeoutError: If the command did not finish in time.

        Returns:
            The exit code.
        """
        if not self._done.wait(timeout):
            raise TimeoutError(
                "Timed out waiting for Docker sandbox command to finish."
            )

        assert self._exit_code is not None
        return self._exit_code

    def kill(self) -> None:
        """Terminate the command by killing its recorded pid."""
        if self._done.is_set():
            return

        try:
            kill_exec = self._client.exec_create(
                self._container_id,
                ["sh", "-c", f'kill -9 "$(cat {self._pid_file})"'],
            )
            self._client.exec_start(kill_exec["Id"])
        except Exception as e:
            logger.warning(
                "DockerSandbox kill() failed: %s",
                e,
                exc_info=True,
            )

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code, or `None` if the command is still running.

        Returns:
            The exit code or `None`.
        """
        return self._exit_code


class DockerSandboxSession(SandboxSession):
    """Docker sandbox session backed by a container."""

    def __init__(
        self,
        container: "Container",
        workdir: str,
        env: Dict[str, str],
        *,
        parent: "BaseSandbox",
        destroy_on_exit: bool = False,
        id: str,
    ) -> None:
        """Initialize the Docker sandbox session.

        Args:
            container: The running container backing this session.
            workdir: Working directory inside the container.
            env: Environment variables to set for this session.
            parent: The sandbox component that created this session.
            destroy_on_exit: Whether to destroy the sandbox session when the
                session context manager exits.
            id: Session ID.
        """
        self._container = container
        self._workdir = workdir
        self._env = env
        super().__init__(
            id=id,
            parent=parent,
            destroy_on_exit=destroy_on_exit,
        )

    def _resolve_path(self, path: str) -> str:
        """Resolve a path against the session working directory.

        Args:
            path: Path to resolve.

        Returns:
            An absolute path inside the container.
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
        """Execute a command in the session container.

        Args:
            command: The command to execute.
            cwd: Optional working directory override. Relative paths are
                resolved against the session workdir. When `None`, the
                session workdir is used.
            env: Environment variables to set in the environment executing
                the command.

        Raises:
            SandboxExecError: If the exec instance fails to launch.

        Returns:
            Process handle.
        """
        if isinstance(command, str):
            command = shlex.split(command)

        self._log_command(command)

        pid_file = f"/tmp/zenml-sandbox-exec-{uuid4().hex[:8]}.pid"
        api = self._container.client.api
        started_at = time.time()
        try:
            exec_instance = api.exec_create(
                self._container.id,
                ["sh", "-c", _PID_FILE_WRAPPER, "sh", pid_file, *command],
                environment={**self._env, **(env or {})},
                workdir=self._resolve_path(cwd) if cwd else self._workdir,
            )
        except Exception as e:
            raise SandboxExecError(
                f"Docker sandbox execution failed to launch: {e}"
            ) from e

        return DockerSandboxProcess(
            client=api,
            container_id=self._container.id,
            exec_id=exec_instance["Id"],
            pid_file=pid_file,
            session=self,
            started_at=started_at,
        )

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file into the session container.

        Args:
            local_path: Source path on the caller's filesystem.
            remote_path: Destination path in the container.
        """
        destination = self._resolve_path(remote_path)
        directory = posixpath.dirname(destination) or "/"

        # `put_archive` requires the destination directory to exist.
        api = self._container.client.api
        mkdir = api.exec_create(self._container.id, ["mkdir", "-p", directory])
        api.exec_start(mkdir["Id"])

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            tar.add(local_path, arcname=posixpath.basename(destination))

        self._container.put_archive(directory, buffer.getvalue())

    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the session container.

        Args:
            remote_path: Source path in the container.
            local_path: Destination path on the caller's filesystem.

        Raises:
            FileNotFoundError: If the remote path does not exist or is not
                a regular file.
        """
        source = self._resolve_path(remote_path)
        try:
            stream, _ = self._container.get_archive(source)
        except NotFound:
            raise FileNotFoundError(
                f"Path `{remote_path}` does not exist in the sandbox."
            )

        buffer = io.BytesIO()
        for chunk in stream:
            buffer.write(chunk)
        buffer.seek(0)

        with tarfile.open(fileobj=buffer) as tar:
            try:
                extracted = tar.extractfile(posixpath.basename(source))
            except KeyError:
                extracted = None

            if extracted is None:
                raise FileNotFoundError(
                    f"Path `{remote_path}` is not a regular file in the "
                    "sandbox."
                )

            with open(local_path, "wb") as destination_file:
                shutil.copyfileobj(extracted, destination_file)

    def _create_snapshot(self) -> SandboxSnapshot:
        """Commit the session container filesystem as a local image.

        Returns:
            A sandbox snapshot referencing the committed image.
        """
        image = self._container.commit(
            repository=_SNAPSHOT_REPOSITORY,
            tag=f"{self.id}-{uuid4().hex[:8]}",
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
        """Release the session handle. The container keeps running."""

    def _destroy(self) -> None:
        """Force-remove the session container."""
        self._container.remove(force=True)


class DockerSandbox(BaseSandbox):
    """Docker daemon-backed sandbox."""

    _docker_engine: Optional[DockerContainerEngine] = None

    @property
    def config(self) -> DockerSandboxConfig:
        """Docker sandbox configuration.

        Returns:
            The Docker sandbox configuration.
        """
        return cast(DockerSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSandboxSettings"]]:
        """Settings class.

        Returns:
            `DockerSandboxSettings`.
        """
        return DockerSandboxSettings

    @property
    def docker_engine(self) -> DockerContainerEngine:
        """Initialize and/or return the docker engine.

        Returns:
            The docker engine.
        """
        if self._docker_engine is None:
            docker_engine = get_container_engine(ContainerEngineType.DOCKER)

            self._docker_engine = cast(DockerContainerEngine, docker_engine)
        return self._docker_engine

    @property
    def docker_client(self) -> DockerClient:
        """Initialize and/or return the docker client.

        Returns:
            The docker client.
        """
        return self.docker_engine.client

    def _ensure_image(self, settings: DockerSandboxSettings) -> None:
        """Make the session image available according to the pull policy.

        Args:
            settings: The resolved session settings.

        Raises:
            RuntimeError: If the image is missing locally and the pull
                policy forbids pulling.
        """
        if settings.pull_policy == DockerSandboxPullPolicy.ALWAYS:
            self.docker_client.images.pull(settings.image)
            return

        try:
            self.docker_client.images.get(settings.image)
        except ImageNotFound:
            if settings.pull_policy == DockerSandboxPullPolicy.NEVER:
                raise RuntimeError(
                    f"Image `{settings.image}` is not available locally and "
                    "the pull policy is set to `never`."
                )

            logger.info("Pulling sandbox image `%s`.", settings.image)
            self.docker_client.images.pull(settings.image)

    def create_session(
        self,
        settings: Optional[BaseSandboxSettings] = None,
        destroy_on_exit: bool = False,
    ) -> SandboxSession:
        """Create a Docker sandbox session backed by a new container.

        Args:
            settings: Optional settings overrides.
            destroy_on_exit: Whether to destroy the sandbox session when the
                session context manager exits.

        Returns:
            A Docker sandbox session.
        """
        settings = cast(DockerSandboxSettings, self.resolve_settings(settings))
        self._ensure_image(settings)

        session_id = f"docker-{uuid4().hex[:12]}"

        run_args = copy.deepcopy(settings.run_args)
        labels = run_args.pop("labels", {})
        labels[_SESSION_ID_LABEL] = session_id
        if settings.cpu_limit is not None:
            run_args["nano_cpus"] = int(settings.cpu_limit * 1e9)
        if settings.memory_limit is not None:
            run_args["mem_limit"] = settings.memory_limit

        container = self.docker_client.containers.run(
            image=settings.image,
            command=["sleep", "infinity"],
            entrypoint=[],
            detach=True,
            name=f"zenml-sandbox-{session_id}",
            labels=labels,
            working_dir=settings.workdir,
            **run_args,
        )

        return DockerSandboxSession(
            container=container,
            workdir=settings.workdir,
            env=self._resolve_session_environment(settings),
            parent=self,
            destroy_on_exit=destroy_on_exit,
            id=session_id,
        )

    def attach(self, session_id: str) -> SandboxSession:
        """Attach to a running Docker sandbox session.

        Args:
            session_id: The ID of the running sandbox session.

        Raises:
            KeyError: If no running session with the given ID exists.

        Returns:
            Sandbox session.
        """
        containers = self.docker_client.containers.list(
            filters={"label": f"{_SESSION_ID_LABEL}={session_id}"}
        )
        if not containers:
            raise KeyError(
                f"No running Docker sandbox session `{session_id}` found."
            )

        settings = cast(DockerSandboxSettings, self.resolve_settings())
        return DockerSandboxSession(
            container=containers[0],
            workdir=settings.workdir,
            env=self._resolve_session_environment(settings),
            parent=self,
            id=session_id,
        )

    def restore(self, snapshot: SandboxSnapshot) -> SandboxSession:
        """Restore a sandbox session from a snapshot.

        Args:
            snapshot: The snapshot to restore from.

        Returns:
            A new session started from the snapshot image.
        """
        self._validate_snapshot(snapshot)
        # Snapshot images are stored locally, so they must never be pulled.
        return self.create_session(
            settings=DockerSandboxSettings(
                image=snapshot.ref,
                pull_policy=DockerSandboxPullPolicy.NEVER,
            )
        )


class DockerSandboxFlavor(BaseSandboxFlavor):
    """Docker sandbox flavor."""

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
