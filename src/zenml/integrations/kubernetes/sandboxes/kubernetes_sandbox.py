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
"""Kubernetes sandbox implementation."""

import base64
import logging
import os
import posixpath
import queue
import re
import shlex
import threading
import time
import uuid
from typing import Dict, Iterator, List, Optional, Tuple, Type, Union, cast

from kubernetes import client as k8s_client
from kubernetes.stream import stream as k8s_stream

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.flavors import (
    KubernetesSandboxConfig,
    KubernetesSandboxSettings,
)
from zenml.integrations.kubernetes.manifest_utils import build_pod_manifest
from zenml.logger import get_logger
from zenml.sandboxes.base import BaseSandbox, BaseSandboxSettings
from zenml.sandboxes.process import SandboxExecError, SandboxProcess
from zenml.sandboxes.session import SandboxSession

logger = get_logger(__name__)

_STREAM_END = object()

# Env var keys are interpolated unquoted into `export <key>=...`, so only
# shell-identifier keys are safe there.
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Per-stream line cap for the websocket drain queues.
_STREAM_BUFFER_MAX_LINES = 100_000

# Characters per stdin frame during file uploads.
_FILE_TRANSFER_CHUNK_CHARS = 1024 * 1024

_FILE_UPLOAD_MAX_BYTES = 256 * 1024 * 1024


def _split_lines_with_buffer(chunk: str, buffer: str) -> Tuple[List[str], str]:
    """Split a chunk into lines and remaining buffer.

    Args:
        chunk: A chunk from a stream.
        buffer: The remaining buffer from previous chunks.

    Returns:
        A tuple of lines and remaining buffer.
    """
    combined = f"{buffer}{chunk}"
    lines = combined.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        return lines[:-1], lines[-1]
    return lines, ""


def _iter_stream_chunks(
    websocket_client: "k8s_stream.ws_client.WSClient",
) -> Iterator[Tuple[str, str]]:
    """Iterate output chunks of a websocket client until it closes.

    Args:
        websocket_client: The websocket client to read from.

    Yields:
        Tuples of channel name (`stdout` or `stderr`) and chunk.
    """
    while websocket_client.is_open():
        websocket_client.update(timeout=1)
        if websocket_client.peek_stdout():
            yield "stdout", websocket_client.read_stdout()
        if websocket_client.peek_stderr():
            yield "stderr", websocket_client.read_stderr()


def _read_exit_code(
    websocket_client: "k8s_stream.ws_client.WSClient",
) -> Optional[int]:
    """Read the exec exit code from a closed websocket client.

    Args:
        websocket_client: The websocket client to read the exit code from.

    Returns:
        The exit code or `None` if it cannot be determined.
    """
    try:
        return cast(Optional[int], websocket_client.returncode)
    except Exception:
        logger.debug(
            "Failed to read Kubernetes sandbox exec exit code.",
            exc_info=True,
        )
        return None


class KubernetesSandboxProcess(SandboxProcess):
    """Handle to a command running in a Kubernetes sandbox session."""

    def __init__(
        self,
        session: "KubernetesSandboxSession",
        websocket_client: "k8s_stream.ws_client.WSClient",
        started_at: float,
    ) -> None:
        """Initialize the Kubernetes sandbox process.

        Args:
            session: The owning sandbox session.
            websocket_client: Kubernetes websocket client for pod exec.
            started_at: The wall-clock time the process started.
        """
        super().__init__(session=session, started_at=started_at)
        self._websocket_client = websocket_client
        self._stdout_queue: "queue.Queue[object]" = queue.Queue()
        self._stderr_queue: "queue.Queue[object]" = queue.Queue()
        self._exit_code: Optional[int] = None
        self._overflow_warned = False
        self._done = threading.Event()
        self._drain_thread = threading.Thread(
            target=self._drain_streams,
            name=f"k8s-sandbox-process-{session.id}",
            daemon=True,
        )
        self._drain_thread.start()

    def _enqueue_line(self, q: "queue.Queue[object]", line: str) -> None:
        """Enqueue a stream line, dropping the oldest lines past the cap.

        Args:
            q: Target stream queue.
            line: Stream line to enqueue.
        """
        while q.qsize() >= _STREAM_BUFFER_MAX_LINES:
            try:
                q.get_nowait()
            except queue.Empty:
                break

            if not self._overflow_warned:
                self._overflow_warned = True
                logger.warning(
                    "Kubernetes sandbox exec output exceeded the %d-line "
                    "buffer, oldest undrained lines are being dropped. "
                    "Drain process.stdout()/stderr() (or use collect()) to "
                    "keep full output.",
                    _STREAM_BUFFER_MAX_LINES,
                )

        q.put(line)

    def _drain_streams(self) -> None:
        """Read stdout/stderr from websocket and feed line queues."""
        stdout_buffer = ""
        stderr_buffer = ""
        try:
            for channel, chunk in _iter_stream_chunks(self._websocket_client):
                if channel == "stdout":
                    lines, stdout_buffer = _split_lines_with_buffer(
                        chunk=chunk, buffer=stdout_buffer
                    )
                    for line in lines:
                        self._enqueue_line(self._stdout_queue, line)
                else:
                    lines, stderr_buffer = _split_lines_with_buffer(
                        chunk=chunk, buffer=stderr_buffer
                    )
                    for line in lines:
                        self._enqueue_line(self._stderr_queue, line)
        except Exception as e:
            logger.debug(
                "Error while draining Kubernetes sandbox streams: %s", e
            )
            if self._exit_code is None:
                self._exit_code = 1
            self._stderr_queue.put(f"Kubernetes sandbox stream failed: {e}\n")
        finally:
            if stdout_buffer:
                self._enqueue_line(self._stdout_queue, stdout_buffer)
            if stderr_buffer:
                self._enqueue_line(self._stderr_queue, stderr_buffer)
            if self._exit_code is None:
                self._exit_code = _read_exit_code(self._websocket_client)
            if self._exit_code is None:
                self._exit_code = 1
            self._stdout_queue.put(_STREAM_END)
            self._stderr_queue.put(_STREAM_END)
            self._done.set()

    @staticmethod
    def _iter_queue(q: "queue.Queue[object]") -> Iterator[str]:
        """Iterate queue items until sentinel is reached.

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
                "Timed out waiting for sandbox command to finish."
            )
        assert self._exit_code is not None
        return self._exit_code

    def kill(self) -> None:
        """Terminate the running command stream."""
        if not self._done.is_set():
            try:
                self._websocket_client.close()
            except Exception as e:
                logger.warning(
                    "KubernetesSandbox kill() failed: %s. Command stream may "
                    "still be active.",
                    e,
                    exc_info=True,
                )

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code or `None` if still running.

        Returns:
            Exit code or `None`.
        """
        return self._exit_code


class KubernetesSandboxSession(SandboxSession):
    """Session for a Kubernetes-backed sandbox pod."""

    def __init__(
        self,
        *,
        id: str,
        pod_name: str,
        namespace: str,
        parent: "BaseSandbox",
    ) -> None:
        """Initialize a Kubernetes sandbox session.

        Args:
            id: Session identifier.
            pod_name: Name of the backing Kubernetes pod.
            namespace: Kubernetes namespace of the pod.
            parent: The sandbox component that created this session.
        """
        self._pod_name = pod_name
        self._namespace = namespace
        self._core_api: Optional[k8s_client.CoreV1Api] = None
        # `kubernetes.stream` swaps `ApiClient.request` in place during exec
        # handshakes, so all calls on the client are serialized behind this lock.
        self._client_lock = threading.Lock()
        super().__init__(id=id, parent=parent)

    def _get_core_api(self) -> k8s_client.CoreV1Api:
        """Get the session-private Kubernetes Core API client.

        Returns:
            The CoreV1Api client.
        """
        sandbox = cast(KubernetesSandbox, self._parent)
        if self._core_api is None or sandbox.connector_has_expired():
            self._core_api = k8s_client.CoreV1Api(sandbox.build_kube_client())

        return self._core_api

    @staticmethod
    def _build_shell_command(
        command: Union[str, List[str]],
        cwd: Optional[str],
        env: Optional[Dict[str, str]],
    ) -> List[str]:
        """Build shell command for pod exec with cwd/env handling.

        Args:
            command: Command to execute.
            cwd: Optional working directory.
            env: Optional environment variables.

        Raises:
            ValueError: If an `env` key is not a valid shell identifier.

        Returns:
            A shell command list suitable for Kubernetes pod exec.
        """
        if isinstance(command, list):
            command_str = " ".join(shlex.quote(part) for part in command)
        else:
            command_str = command

        if env:
            for key in env:
                if not _ENV_KEY_PATTERN.fullmatch(key):
                    raise ValueError(
                        f"Invalid environment variable name {key!r}: must "
                        "match [A-Za-z_][A-Za-z0-9_]*."
                    )
            exports = "".join(
                f"export {key}={shlex.quote(value)}; "
                for key, value in env.items()
            )
            command_str = f"{exports}{command_str}"

        if cwd:
            # The group is terminated with a newline rather than `; }`: a
            # raw string command ending in `#comment`, `;` or `&` would
            # swallow or clash with `; }`, while a newline ends comments
            # and is a valid command terminator in all cases.
            command_str = f"cd {shlex.quote(cwd)} && {{ {command_str}\n}}"

        return ["/bin/sh", "-c", command_str]

    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Execute a command in the sandbox pod.

        Args:
            command: The command to execute.
            cwd: Optional working directory override.
            env: Optional environment variables to set in the command process.

        Returns:
            Process handle.
        """
        self._log_command(command)

        exec_command = self._build_shell_command(
            command=command, cwd=cwd, env=env
        )
        started_at = time.time()
        websocket_client = self._open_exec_stream(command=exec_command)

        return KubernetesSandboxProcess(
            session=self,
            websocket_client=websocket_client,
            started_at=started_at,
        )

    def _open_exec_stream(
        self, command: List[str], stdin: bool = False
    ) -> "k8s_stream.ws_client.WSClient":
        """Open a websocket exec stream in the sandbox pod.

        Args:
            command: Command to execute.
            stdin: Whether to open a stdin channel.

        Raises:
            SandboxExecError: If command execution cannot be started.

        Returns:
            The websocket client.
        """
        try:
            with self._client_lock:
                return k8s_stream(
                    self._get_core_api().connect_get_namespaced_pod_exec,
                    self._pod_name,
                    self._namespace,
                    command=command,
                    stderr=True,
                    stdin=stdin,
                    stdout=True,
                    tty=False,
                    _preload_content=False,
                )
        except Exception as e:
            raise SandboxExecError(
                f"Kubernetes sandbox execution failed to launch: {e}"
            ) from e

    @staticmethod
    def _collect_exec_output(
        websocket_client: "k8s_stream.ws_client.WSClient",
    ) -> str:
        """Collect exec output until the command finishes.

        Args:
            websocket_client: The websocket client to drain.

        Raises:
            SandboxExecError: If the command fails.

        Returns:
            The captured stdout.
        """
        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []
        for channel, chunk in _iter_stream_chunks(websocket_client):
            if channel == "stdout":
                stdout_chunks.append(chunk)
            else:
                stderr_chunks.append(chunk)

        if _read_exit_code(websocket_client) != 0:
            stderr = "".join(stderr_chunks)
            raise SandboxExecError(
                f"Kubernetes sandbox file transfer failed: {stderr.strip()}"
            )

        return "".join(stdout_chunks)

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to the sandbox pod.

        Args:
            local_path: Path of the local file to upload.
            remote_path: Destination path in the sandbox pod.

        Raises:
            ValueError: If the file exceeds the upload size limit.
        """
        if os.path.getsize(local_path) > _FILE_UPLOAD_MAX_BYTES:
            raise ValueError(
                f"File `{local_path}` exceeds the "
                f"{_FILE_UPLOAD_MAX_BYTES} byte upload limit."
            )

        # The file content is transferred base64-encoded because the
        # websocket client decodes frames as UTF-8, which corrupts raw
        # binary.
        with open(local_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")

        # `head -c N` makes the remote pipeline exit after the exact encoded
        # byte count, since the websocket client cannot signal stdin EOF.
        parent_dir = posixpath.dirname(remote_path) or "."
        script = (
            f"mkdir -p {shlex.quote(parent_dir)} && "
            f"head -c {len(encoded)} | base64 -d > {shlex.quote(remote_path)}"
        )
        websocket_client = self._open_exec_stream(
            command=["/bin/sh", "-c", script], stdin=True
        )
        for index in range(0, len(encoded), _FILE_TRANSFER_CHUNK_CHARS):
            websocket_client.write_stdin(
                encoded[index : index + _FILE_TRANSFER_CHUNK_CHARS]
            )

        self._collect_exec_output(websocket_client)

    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the sandbox pod.

        Args:
            remote_path: Path of the file in the sandbox pod.
            local_path: Local destination path.
        """
        websocket_client = self._open_exec_stream(
            command=["/bin/sh", "-c", f"base64 < {shlex.quote(remote_path)}"]
        )
        stdout = self._collect_exec_output(websocket_client)

        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        with open(local_path, "wb") as f:
            f.write(base64.b64decode(stdout))

    def _close(self) -> None:
        """Close session handle without terminating the pod."""

    def _destroy(self) -> None:
        """Delete the backing sandbox pod from Kubernetes."""
        sandbox = cast(KubernetesSandbox, self._parent)
        with self._client_lock:
            kube_utils.delete_pod(
                core_api=self._get_core_api(),
                pod_name=self._pod_name,
                namespace=self._namespace,
                api_request_timeout=sandbox.config.api_request_timeout,
            )


class KubernetesSandbox(BaseSandbox):
    """Kubernetes pod-backed sandbox."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def config(self) -> KubernetesSandboxConfig:
        """Kubernetes sandbox configuration.

        Returns:
            The Kubernetes sandbox configuration.
        """
        return cast(KubernetesSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class.

        Returns:
            `KubernetesSandboxSettings`.
        """
        return KubernetesSandboxSettings

    def build_kube_client(self) -> k8s_client.ApiClient:
        """Build a new Kubernetes API client.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: If the service connector returns an unexpected client.
        """
        if self.config.incluster:
            kube_utils.load_kube_config(incluster=True)
            return k8s_client.ApiClient()

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use "
                    f"the linked connector, but got {type(client)}."
                )

            return client

        kube_utils.load_kube_config(
            context=self.config.kubernetes_context,
        )

        return k8s_client.ApiClient()

    def get_kube_client(self) -> k8s_client.ApiClient:
        """Get the cached Kubernetes API client.

        Returns:
            The Kubernetes API client.
        """
        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        self._k8s_client = self.build_kube_client()

        return self._k8s_client

    @property
    def core_api(self) -> k8s_client.CoreV1Api:
        """Get the Kubernetes Core API client.

        Returns:
            The CoreV1Api client.
        """
        return k8s_client.CoreV1Api(self.get_kube_client())

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Create a sandbox session backed by a Kubernetes pod.

        Args:
            settings: Optional settings overrides.

        Raises:
            Exception: If the sandbox pod fails to start.

        Returns:
            A Kubernetes sandbox session.
        """
        resolved_settings = cast(
            KubernetesSandboxSettings, self.resolve_settings(settings)
        )
        session_id = f"k8s-{uuid.uuid4().hex[:12]}"
        pod_name = kube_utils.sanitize_label(f"zenml-sandbox-{session_id}")
        labels = {
            "zenml-sandbox-id": kube_utils.sanitize_label_value(session_id),
            "zenml-sandbox-component-id": kube_utils.sanitize_label_value(
                str(self.id)
            ),
        }
        env = self._resolve_session_environment(resolved_settings)
        pod_manifest = build_pod_manifest(
            pod_name=pod_name,
            image_name=resolved_settings.image,
            command=["/bin/sh", "-c"],
            args=["while true; do sleep 30; done"],
            privileged=resolved_settings.privileged,
            pod_settings=resolved_settings.pod_settings,
            service_account_name=resolved_settings.service_account_name,
            env=env,
            labels=labels,
        )
        if pod_manifest.spec is not None:
            pod_manifest.spec.automount_service_account_token = (
                resolved_settings.automount_service_account_token
            )

        kube_utils.create_pod(
            core_api=self.core_api,
            namespace=self.config.kubernetes_namespace,
            pod_manifest=pod_manifest,
            api_request_timeout=resolved_settings.api_request_timeout,
        )

        try:
            kube_utils.wait_pod(
                kube_client_fn=self.get_kube_client,
                pod_name=pod_name,
                namespace=self.config.kubernetes_namespace,
                exit_condition_lambda=lambda pod: (
                    pod.status is not None
                    and pod.status.phase == kube_utils.PodPhase.RUNNING.value
                ),
                timeout_sec=resolved_settings.pod_startup_timeout,
                api_request_timeout=resolved_settings.api_request_timeout,
            )
        except Exception:
            try:
                kube_utils.delete_pod(
                    core_api=self.core_api,
                    pod_name=pod_name,
                    namespace=self.config.kubernetes_namespace,
                    api_request_timeout=resolved_settings.api_request_timeout,
                )
            except Exception:
                logger.debug(
                    "Failed to clean up Kubernetes sandbox pod `%s` "
                    "after startup failure.",
                    pod_name,
                    exc_info=True,
                )
            raise

        return KubernetesSandboxSession(
            id=session_id,
            pod_name=pod_name,
            namespace=self.config.kubernetes_namespace,
            parent=self,
        )

    def attach(self, session_id: str) -> SandboxSession:
        """Attach to a running sandbox session.

        Args:
            session_id: The ID of the running sandbox session.

        Raises:
            RuntimeError: If no pod exists for the session, the pod belongs
                to a different sandbox component, or the pod is not running.

        Returns:
            A Kubernetes sandbox session.
        """
        pods = kube_utils.retry_on_api_exception(
            self.core_api.list_namespaced_pod,
            api_request_timeout=self.config.api_request_timeout,
        )(
            namespace=self.config.kubernetes_namespace,
            label_selector=(
                f"zenml-sandbox-id="
                f"{kube_utils.sanitize_label_value(session_id)}"
            ),
        )
        if not pods.items:
            raise RuntimeError(
                f"No sandbox pod found for session `{session_id}`."
            )

        pod = pods.items[0]
        labels = pod.metadata.labels or {}
        if labels.get(
            "zenml-sandbox-component-id"
        ) != kube_utils.sanitize_label_value(str(self.id)):
            raise RuntimeError(
                f"Sandbox pod for session `{session_id}` belongs to a "
                "different sandbox component."
            )

        if (
            pod.status is None
            or pod.status.phase != kube_utils.PodPhase.RUNNING.value
        ):
            raise RuntimeError(
                f"Sandbox pod for session `{session_id}` is not running."
            )

        return KubernetesSandboxSession(
            id=session_id,
            pod_name=pod.metadata.name,
            namespace=self.config.kubernetes_namespace,
            parent=self,
        )
