#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Modal sandbox implementation."""

import asyncio
import inspect
import json
import socket
import time
from contextlib import nullcontext
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
)
from uuid import uuid4

from zenml.client import Client
from zenml.integrations.modal.flavors import (
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.integrations.modal.utils import (
    build_modal_image,
    map_resource_settings,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    CodeInterpreter,
    NetworkPolicy,
    SandboxCapability,
    SandboxExecError,
    SandboxExecResult,
    SandboxProcess,
    SandboxSession,
    SandboxSessionMetadata,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings

logger = get_logger(__name__)
_COMMAND_ROUTER_INIT_TIMEOUT_SECONDS = 5.0

_INTERPRETER_BOOTSTRAP = r"""
import contextlib
import io
import json
import traceback
import sys


def _serialize_output(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


globals_ns = {}
while True:
    line = sys.stdin.readline()
    if not line:
        break

    request = json.loads(line)
    code = request.get("code", "")
    inputs = request.get("inputs") or {}

    if isinstance(inputs, dict):
        globals_ns.update(inputs)

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    output = None
    exit_code = 0

    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        try:
            exec(code, globals_ns, globals_ns)
            output = globals_ns.get("output")
        except Exception:
            exit_code = 1
            traceback.print_exc(file=stderr_buffer)

    response = {
        "exit_code": exit_code,
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
        "output": _serialize_output(output),
    }
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()
"""


def _decode_output(output: Any) -> str:
    """Normalizes process output to UTF-8 text."""
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)


def _run_awaitable(value: Any) -> Any:
    """Runs awaitables synchronously when needed."""
    if not inspect.isawaitable(value):
        return value

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(value)

    raise RuntimeError(
        "Modal sandbox sync interface cannot run while an event loop is "
        "already active."
    )


def _call_modal(method: Any, *args: Any, **kwargs: Any) -> Any:
    """Calls a Modal method and resolves sync/async results."""
    return _run_awaitable(method(*args, **kwargs))


def _read_stream(stream: Any) -> str:
    """Reads full stream content and normalizes it to text."""
    if stream is None:
        return ""

    read_method = getattr(stream, "read", None)
    if not callable(read_method):
        return ""

    return _decode_output(_call_modal(read_method))


def _iter_stream(stream: Any) -> Iterator[str]:
    """Yields stream output line-by-line."""
    if stream is None:
        return

    readline_method = getattr(stream, "readline", None)
    if callable(readline_method):
        while True:
            line = _decode_output(_call_modal(readline_method))
            if not line:
                break
            yield line
        return

    for chunk in stream:
        yield _decode_output(chunk)


def _wait_for_process(
    process: Any, timeout_seconds: Optional[int] = None
) -> int:
    """Waits for process completion and returns its exit code."""
    poll_method = getattr(process, "poll", None)
    if timeout_seconds is not None and callable(poll_method):
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            poll_result = _call_modal(poll_method)
            if poll_result is not None:
                return int(poll_result)
            time.sleep(0.1)
        return -1

    wait_method = getattr(process, "wait", None)
    wait_result: Optional[Any] = None
    if callable(wait_method):
        wait_result = _call_modal(wait_method)

    exit_code = getattr(process, "returncode", None)
    if exit_code is None and isinstance(wait_result, int):
        exit_code = wait_result

    return int(exit_code) if exit_code is not None else 0


def _estimate_modal_cost_usd(
    *,
    duration_seconds: float,
    cpu: float,
    memory_mb: int,
    cpu_cost_per_core_second_usd: float,
    memory_cost_per_gib_second_usd: float,
) -> float:
    """Computes a best-effort Modal sandbox session cost estimate."""
    safe_duration_seconds = max(0.0, duration_seconds)
    safe_cpu = max(0.0, cpu)
    safe_memory_gib = max(0, memory_mb) / 1024.0

    cpu_cost = safe_duration_seconds * safe_cpu * cpu_cost_per_core_second_usd
    memory_cost = (
        safe_duration_seconds
        * safe_memory_gib
        * memory_cost_per_gib_second_usd
    )
    return cpu_cost + memory_cost


def _write_to_stream(stream: Any, payload: str) -> None:
    """Writes text payload into a process stream."""
    if stream is None:
        raise RuntimeError("Missing process stdin handle.")

    try:
        stream.write(payload)
    except TypeError:
        stream.write(payload.encode("utf-8"))

    drain_method = getattr(stream, "drain", None)
    if callable(drain_method):
        _call_modal(drain_method)
        return

    flush_method = getattr(stream, "flush", None)
    if callable(flush_method):
        _call_modal(flush_method)


def _readline_from_stream(stream: Any) -> str:
    """Reads one line from a process stream."""
    if stream is None:
        raise RuntimeError("Missing process stdout handle.")

    readline_method = getattr(stream, "readline", None)
    if callable(readline_method):
        return _decode_output(_call_modal(readline_method))

    iter_method = getattr(stream, "__iter__", None)
    if callable(iter_method):
        iterator = iter(stream)
        try:
            return _decode_output(next(iterator))
        except StopIteration:
            return ""

    raise RuntimeError("Process stdout handle does not support line reads.")


def _close_modal_context(context: Any, is_async: bool) -> None:
    """Closes a Modal context manager regardless of sync/async implementation."""
    if context is None:
        return

    if is_async:
        aexit = getattr(context, "__aexit__", None)
        if callable(aexit):
            _run_awaitable(aexit(None, None, None))
        return

    exit_method = getattr(context, "__exit__", None)
    if callable(exit_method):
        exit_method(None, None, None)


def _is_command_router_disabled(sandbox: Any) -> bool:
    """Returns whether command-router initialization was previously disabled."""
    if getattr(sandbox, "_zenml_command_router_disabled", False):
        return True

    sandbox_dict = getattr(sandbox, "__dict__", {})
    if isinstance(sandbox_dict, dict):
        for key, value in sandbox_dict.items():
            if isinstance(key, str) and key.startswith("_sync_original_"):
                if getattr(value, "_zenml_command_router_disabled", False):
                    return True

    return False


def _patch_command_router_fallback(sandbox: Any) -> None:
    """Patches Modal command router resolution to degrade gracefully.

    Some environments fail DNS resolution for worker router hostnames. In that
    case we fall back to the server-side exec path instead of failing commands.
    """
    patch_targets: List[tuple[str, Any]] = [("sandbox", sandbox)]
    sandbox_dict = getattr(sandbox, "__dict__", {})
    if isinstance(sandbox_dict, dict):
        for key, value in sandbox_dict.items():
            if isinstance(key, str) and key.startswith("_sync_original_"):
                patch_targets.append((key, value))

    seen_target_ids = set()
    warned = False
    router_disabled = False
    patched_targets = 0

    for target_name, target in patch_targets:
        target_id = id(target)
        if target_id in seen_target_ids:
            continue
        seen_target_ids.add(target_id)

        get_router_client = getattr(target, "_get_command_router_client", None)
        if not callable(get_router_client):
            continue

        if not hasattr(target, "_zenml_command_router_disabled"):
            try:
                target._zenml_command_router_disabled = False
            except Exception:
                logger.debug(
                    "Unable to initialize command-router disabled state "
                    "for %s.",
                    target_name,
                    exc_info=True,
                )

        async def _safe_get_command_router_client(
            task_id: str,
            _original_get_router_client: Any = get_router_client,
        ) -> Any:
            nonlocal warned, router_disabled
            if router_disabled:
                return None

            try:
                result = _original_get_router_client(task_id)
                if inspect.isawaitable(result):
                    return await asyncio.wait_for(
                        result,
                        timeout=_COMMAND_ROUTER_INIT_TIMEOUT_SECONDS,
                    )
                return result
            except (socket.gaierror, asyncio.TimeoutError) as e:
                router_disabled = True
                for _, patched_target in patch_targets:
                    try:
                        patched_target._zenml_command_router_disabled = True
                    except Exception:
                        logger.debug(
                            "Unable to persist command-router disabled state "
                            "for %s.",
                            patched_target,
                            exc_info=True,
                        )
                if not warned:
                    logger.warning(
                        "Modal command router unavailable; falling back to "
                        "server-side exec path and disabling future direct "
                        "router attempts for this sandbox. Error: %s",
                        e,
                    )
                    warned = True
                return None

        try:
            target._get_command_router_client = _safe_get_command_router_client
            patched_targets += 1
        except Exception:
            logger.debug(
                "Unable to patch Modal command router fallback for %s.",
                target_name,
                exc_info=True,
            )

    logger.debug(
        "Applied Modal command-router fallback patch to %d target(s).",
        patched_targets,
    )


class ModalSandboxProcess(SandboxProcess):
    """Streaming process wrapper for Modal sandbox exec handles.

    Log forwarding happens while stdout/stderr iterators are consumed.
    """

    def __init__(self, process: Any, terminate_session: Any) -> None:
        """Initializes the process wrapper.

        Args:
            process: Underlying Modal process handle.
            terminate_session: Callback used as cancellation fallback.
        """
        self._process = process
        self._terminate_session = terminate_session
        self._cached_exit_code: Optional[int] = None

    def stdout_iter(self) -> Iterator[str]:
        """Iterates over stdout chunks as they are produced."""
        for line in _iter_stream(getattr(self._process, "stdout", None)):
            logger.info("[sandbox:stdout] %s", line.rstrip("\n"))
            yield line

    def stderr_iter(self) -> Iterator[str]:
        """Iterates over stderr chunks as they are produced."""
        for line in _iter_stream(getattr(self._process, "stderr", None)):
            logger.warning("[sandbox:stderr] %s", line.rstrip("\n"))
            yield line

    def wait(self, timeout_seconds: Optional[int] = None) -> int:
        """Waits for process completion and returns the exit code."""
        self._cached_exit_code = _wait_for_process(
            self._process, timeout_seconds=timeout_seconds
        )
        return self._cached_exit_code

    @property
    def exit_code(self) -> Optional[int]:
        """Returns the process exit code when available."""
        if self._cached_exit_code is not None:
            return self._cached_exit_code

        process_exit_code = getattr(self._process, "returncode", None)
        if process_exit_code is None:
            return None
        return int(process_exit_code)

    def kill(self) -> None:
        """Cancels execution by terminating the entire sandbox session."""
        self._terminate_session(reason="process kill requested")


class ModalCodeInterpreter(CodeInterpreter):
    """Persistent Python interpreter running inside a Modal sandbox."""

    def __init__(
        self,
        session: "ModalSandboxSession",
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """Initializes the interpreter.

        Args:
            session: Parent sandbox session.
            timeout_seconds: Optional timeout used to start the interpreter.
        """
        self._session = session
        self._timeout_seconds = timeout_seconds
        self._process: Optional[Any] = None
        self._stdin: Optional[Any] = None
        self._stdout: Optional[Any] = None

    def __enter__(self) -> "ModalCodeInterpreter":
        """Starts the interpreter process."""
        self._process = self._session._exec_process(
            ["python", "-u", "-c", _INTERPRETER_BOOTSTRAP],
            timeout_seconds=self._timeout_seconds,
            text=True,
            bufsize=1,
        )
        self._stdin = getattr(self._process, "stdin", None)
        self._stdout = getattr(self._process, "stdout", None)

        if self._stdin is None or self._stdout is None:
            raise RuntimeError(
                "Modal code interpreter requires stdin/stdout process streams."
            )

        return self

    def run(
        self,
        code: str,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> SandboxExecResult:
        """Executes code while preserving state between calls."""
        if self._process is None:
            self.__enter__()

        if timeout_seconds is not None:
            logger.debug(
                "Ignoring timeout_seconds=%s for Modal code interpreter run; "
                "the interpreter protocol currently does not enforce per-call "
                "timeouts.",
                timeout_seconds,
            )

        request = {"code": code, "inputs": inputs or {}}
        _write_to_stream(self._stdin, json.dumps(request) + "\n")
        response_line = _readline_from_stream(self._stdout)

        if not response_line:
            raise RuntimeError("Modal code interpreter returned no response.")

        response = json.loads(response_line)
        result = SandboxExecResult(
            exit_code=int(response.get("exit_code", 1)),
            stdout=_decode_output(response.get("stdout", "")),
            stderr=_decode_output(response.get("stderr", "")),
            output=response.get("output"),
        )

        if self._session.raise_on_failure and result.exit_code != 0:
            raise SandboxExecError(result)

        return result

    def __exit__(self, *args: Any) -> None:
        """Stops the interpreter process."""
        if self._process is None:
            return

        write_eof_method = getattr(self._stdin, "write_eof", None)
        if callable(write_eof_method):
            _call_modal(write_eof_method)

        drain_method = getattr(self._stdin, "drain", None)
        if callable(drain_method):
            _call_modal(drain_method)
        else:
            close_method = getattr(self._stdin, "close", None)
            if callable(close_method):
                _call_modal(close_method)

        _wait_for_process(self._process, timeout_seconds=5)
        self._process = None
        self._stdin = None
        self._stdout = None


class ModalSandboxSession(SandboxSession):
    """Wraps a Modal sandbox handle as a ZenML SandboxSession."""

    def __init__(
        self,
        sandbox: Any,
        *,
        app_run_context: Any,
        app_run_context_is_async: bool,
        raise_on_failure: bool,
        metadata: SandboxSessionMetadata,
        cpu: Optional[float],
        memory_mb: Optional[int],
        gpu: Optional[str],
        cpu_cost_per_core_second_usd: Optional[float],
        memory_cost_per_gib_second_usd: Optional[float],
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> None:
        """Initializes a sandbox session wrapper.

        Args:
            sandbox: Underlying Modal sandbox handle.
            app_run_context: Active Modal app run context.
            app_run_context_is_async: Whether the run context is async.
            raise_on_failure: Default failure mode for exec operations.
            metadata: Metadata instance tracked by the component.
            cpu: Effective CPU assigned to this sandbox session.
            memory_mb: Effective memory assigned to this sandbox session.
            gpu: Effective GPU assigned to this sandbox session.
            cpu_cost_per_core_second_usd: Optional cost rate for one CPU
                core-second.
            memory_cost_per_gib_second_usd: Optional cost rate for one GiB
                second of memory usage.
            env: Default environment variables for command execution.
            workdir: Default working directory for command execution.
        """
        self._sandbox = sandbox
        self._app_run_context = app_run_context
        self._app_run_context_is_async = app_run_context_is_async
        self._raise_on_failure = raise_on_failure
        self._metadata = metadata
        self._default_env = dict(env or {})
        self._workdir = workdir
        self._cpu = cpu
        self._memory_mb = memory_mb
        self._gpu = gpu
        self._cpu_cost_per_core_second_usd = cpu_cost_per_core_second_usd
        self._memory_cost_per_gib_second_usd = memory_cost_per_gib_second_usd
        self._created_at = time.monotonic()
        self._terminated = False
        self._router_fallback_retry_logged = False

    @property
    def raise_on_failure(self) -> bool:
        """Returns default failure behavior for this session."""
        return self._raise_on_failure

    def _exec_process(
        self,
        command: List[str],
        *,
        timeout_seconds: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        text: bool = True,
        bufsize: int = -1,
    ) -> Any:
        """Executes a command in the Modal sandbox and returns the process."""
        if not command:
            raise ValueError("Cannot execute an empty command in a sandbox.")

        exec_kwargs: Dict[str, Any] = {}
        effective_env = dict(self._default_env)
        if env:
            effective_env.update(env)
        if effective_env:
            exec_kwargs["env"] = effective_env

        if timeout_seconds is not None:
            exec_kwargs["timeout"] = timeout_seconds

        effective_workdir = workdir if workdir is not None else self._workdir
        if effective_workdir:
            exec_kwargs["workdir"] = effective_workdir

        exec_kwargs["text"] = text
        exec_kwargs["bufsize"] = bufsize

        try:
            return _call_modal(self._sandbox.exec, *command, **exec_kwargs)
        except socket.gaierror as e:
            if not self._router_fallback_retry_logged:
                logger.warning(
                    "Modal command execution failed while initializing the "
                    "direct command router. Retrying with server-side exec "
                    "fallback. Error: %s",
                    e,
                )
                self._router_fallback_retry_logged = True

            _patch_command_router_fallback(self._sandbox)
            return _call_modal(self._sandbox.exec, *command, **exec_kwargs)

    def _finalize_metadata(self) -> None:
        """Updates duration metadata based on wall-clock runtime."""
        self._metadata.duration_seconds = max(
            self._metadata.duration_seconds,
            time.monotonic() - self._created_at,
        )

        self._metadata.extra["cpu"] = self._cpu
        self._metadata.extra["memory_mb"] = self._memory_mb
        self._metadata.extra["gpu"] = self._gpu

        if (
            self._cpu is None
            or self._memory_mb is None
            or self._cpu_cost_per_core_second_usd is None
            or self._memory_cost_per_gib_second_usd is None
        ):
            self._metadata.extra["estimated_cost_reason"] = (
                "missing resource values or pricing rates"
            )
            return

        estimated_cost_usd = _estimate_modal_cost_usd(
            duration_seconds=self._metadata.duration_seconds,
            cpu=self._cpu,
            memory_mb=self._memory_mb,
            cpu_cost_per_core_second_usd=self._cpu_cost_per_core_second_usd,
            memory_cost_per_gib_second_usd=(
                self._memory_cost_per_gib_second_usd
            ),
        )
        self._metadata.estimated_cost_usd = estimated_cost_usd
        self._metadata.extra["estimated_cost_breakdown"] = {
            "duration_seconds": self._metadata.duration_seconds,
            "cpu": self._cpu,
            "memory_mb": self._memory_mb,
            "memory_gib": self._memory_mb / 1024.0,
            "cpu_cost_per_core_second_usd": (
                self._cpu_cost_per_core_second_usd
            ),
            "memory_cost_per_gib_second_usd": (
                self._memory_cost_per_gib_second_usd
            ),
            "estimated_cost_usd": estimated_cost_usd,
        }

    def exec_run(
        self,
        command: List[str],
        *,
        timeout_seconds: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        check: Optional[bool] = None,
    ) -> SandboxExecResult:
        """Runs a command and returns the collected result."""
        process = self._exec_process(
            command,
            timeout_seconds=timeout_seconds,
            env=env,
            workdir=workdir,
        )
        self._metadata.commands_executed += 1

        stdout = _read_stream(getattr(process, "stdout", None))
        stderr = _read_stream(getattr(process, "stderr", None))
        exit_code = _wait_for_process(process, timeout_seconds=timeout_seconds)

        result = SandboxExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )
        should_check = check if check is not None else self._raise_on_failure
        if should_check and result.exit_code != 0:
            raise SandboxExecError(result)

        return result

    def exec_streaming(
        self,
        command: List[str],
        *,
        timeout_seconds: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> SandboxProcess:
        """Runs a command and yields streaming process output.

        The returned process forwards log lines to ZenML logging while callers
        consume stdout and stderr iterators.
        """
        process = self._exec_process(
            command,
            timeout_seconds=timeout_seconds,
            env=env,
            workdir=workdir,
        )
        self._metadata.commands_executed += 1
        return ModalSandboxProcess(process, self.terminate)

    def run_code(
        self,
        code: str,
        *,
        language: str = "python",
        inputs: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        check: Optional[bool] = None,
    ) -> SandboxExecResult:
        """Runs code inside the sandbox and returns the execution result."""
        if language != "python":
            raise NotImplementedError(
                "ModalSandboxSession.run_code currently only supports "
                "language='python'."
            )

        script_path = "/tmp/_zenml_run.py"
        script = code
        if inputs:
            serialized_inputs = json.dumps(inputs)
            script = (
                "import json\n"
                f"_zenml_inputs = json.loads({serialized_inputs!r})\n"
                "globals().update(_zenml_inputs)\n"
                f"{code}"
            )

        self.write_file(script_path, script)
        return self.exec_run(
            ["python", script_path],
            timeout_seconds=timeout_seconds,
            check=check,
        )

    def code_interpreter(self) -> CodeInterpreter:
        """Creates a persistent Python interpreter for repeated execution."""
        if _is_command_router_disabled(self._sandbox):
            raise RuntimeError(
                "Modal code interpreter requires a direct command router "
                "connection. This sandbox is running in server-side fallback "
                "mode because command-router initialization failed."
            )
        return ModalCodeInterpreter(self)

    def write_file(self, remote_path: str, content: Union[bytes, str]) -> None:
        """Writes content to a file in the sandbox filesystem."""
        mode = "w" if isinstance(content, str) else "wb"
        with self._sandbox.open(remote_path, mode) as remote_file:
            remote_file.write(content)

    def read_file(self, remote_path: str) -> bytes:
        """Reads file content from the sandbox filesystem."""
        with self._sandbox.open(remote_path, "rb") as remote_file:
            data = remote_file.read()
            if isinstance(data, bytes):
                return data
            return _decode_output(data).encode("utf-8")

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file to the sandbox filesystem."""
        content = Path(local_path).read_bytes()
        self.write_file(remote_path, content)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a sandbox file to local storage."""
        Path(local_path).write_bytes(self.read_file(remote_path))

    def snapshot(self) -> Optional[str]:
        """Creates a snapshot of the sandbox filesystem state."""
        snapshot_method = getattr(self._sandbox, "snapshot_filesystem", None)
        if not callable(snapshot_method):
            return None

        snapshot = _call_modal(snapshot_method)
        if snapshot is None:
            return None

        object_id = getattr(snapshot, "object_id", None)
        return str(object_id) if object_id is not None else str(snapshot)

    def open_tunnel(self, port: int) -> Optional[str]:
        """Opens a tunnel to a sandbox port."""
        tunnels_method = getattr(self._sandbox, "tunnels", None)
        if not callable(tunnels_method):
            return None

        tunnels = _call_modal(tunnels_method)
        if not hasattr(tunnels, "get"):
            return None

        tunnel = tunnels.get(port)
        if tunnel is None:
            return None

        url = getattr(tunnel, "url", None) or getattr(tunnel, "web_url", None)
        return str(url) if url else None

    def terminate(self, reason: Optional[str] = None) -> None:
        """Terminates the active sandbox session."""
        if self._terminated:
            return

        if reason:
            logger.debug("Terminating Modal sandbox session: %s", reason)

        terminate_method = getattr(self._sandbox, "terminate", None)
        try:
            if callable(terminate_method):
                _call_modal(terminate_method)
        finally:
            _close_modal_context(
                self._app_run_context, self._app_run_context_is_async
            )
            self._terminated = True
            self._finalize_metadata()

    def __enter__(self) -> "SandboxSession":
        """Enters the sandbox session context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exits the sandbox session context manager."""
        self.terminate(reason="session context exited")


class ModalSandbox(BaseSandbox):
    """Modal implementation of the ZenML sandbox stack component."""

    @property
    def config(self) -> ModalSandboxConfig:
        """Typed Modal sandbox configuration."""
        return cast(ModalSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for step-level sandbox overrides."""
        return ModalSandboxSettings

    @property
    def capabilities(self) -> Set[SandboxCapability]:
        """Capabilities supported by the Modal sandbox provider."""
        return {
            SandboxCapability.FILESYSTEM,
            SandboxCapability.NETWORKING,
            SandboxCapability.TUNNELS,
            SandboxCapability.SNAPSHOTS,
            SandboxCapability.STREAMING_OUTPUT,
            SandboxCapability.PERSISTENT_SESSIONS,
            SandboxCapability.GPU,
        }

    def _resolve_step_settings(self) -> ModalSandboxSettings:
        """Resolves step-level settings if called from inside a running step."""
        base_settings = ModalSandboxSettings.model_validate(
            self.config.model_dump(exclude_unset=True)
        )

        try:
            from zenml.steps import get_step_context

            step_context = get_step_context()
            return cast(
                ModalSandboxSettings, self.get_settings(step_context.step_run)
            )
        except RuntimeError:
            return base_settings
        except Exception:
            logger.debug(
                "Failed to resolve Modal sandbox step settings. Falling back "
                "to component defaults.",
                exc_info=True,
            )
            return base_settings

    def _resolve_secret_env(self, secret_refs: List[str]) -> Dict[str, str]:
        """Resolves secret references to environment key-value pairs."""
        if not secret_refs:
            return {}

        client = Client()
        env: Dict[str, str] = {}
        for secret_ref in secret_refs:
            secret = client.get_secret(secret_ref)
            for key, value in secret.secret_values.items():
                env[key] = str(value)

        return env

    def session(
        self,
        *,
        image: Optional[str] = None,
        cpu: Optional[float] = None,
        memory_mb: Optional[int] = None,
        gpu: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        secret_refs: Optional[List[str]] = None,
        network_policy: Optional[NetworkPolicy] = None,
        tags: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> SandboxSession:
        """Creates a Modal sandbox session and returns its context manager."""
        import modal

        step_settings = self._resolve_step_settings()

        effective_image = (
            image or step_settings.image or self.config.default_image
        )
        effective_timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else (
                step_settings.timeout_seconds
                if step_settings.timeout_seconds is not None
                else self.config.default_timeout_seconds
            )
        )
        effective_cpu = (
            cpu
            if cpu is not None
            else (
                step_settings.cpu
                if step_settings.cpu is not None
                else self.config.default_cpu
            )
        )
        effective_memory_mb = (
            memory_mb
            if memory_mb is not None
            else (
                step_settings.memory_mb
                if step_settings.memory_mb is not None
                else self.config.default_memory_mb
            )
        )
        effective_gpu = (
            gpu if gpu is not None else cast(Optional[str], step_settings.gpu)
        )

        effective_env = dict(step_settings.env or {})
        if env:
            effective_env.update(env)

        effective_secret_refs = list(
            secret_refs
            if secret_refs is not None
            else (step_settings.secret_refs or [])
        )
        secret_env = self._resolve_secret_env(effective_secret_refs)
        effective_env = {**secret_env, **effective_env}

        effective_tags = dict(step_settings.tags or {})
        if tags:
            effective_tags.update(tags)

        if network_policy is not None:
            effective_network_policy = network_policy
        elif step_settings.network_policy is not None:
            effective_network_policy = step_settings.network_policy
        else:
            effective_network_policy = NetworkPolicy(
                block_network=step_settings.block_network,
                cidr_allowlist=step_settings.cidr_allowlist,
            )

        app = modal.App(self.config.app_name)
        modal_image = build_modal_image(base_image=effective_image)

        app_run_context = app.run()
        app_run_context_is_async = False
        enter = getattr(app_run_context, "__enter__", None)
        aenter = getattr(app_run_context, "__aenter__", None)
        if callable(enter):
            enter()
        elif callable(aenter):
            app_run_context_is_async = True
            _run_awaitable(aenter())
        else:
            raise RuntimeError(
                "Modal app run context manager does not support enter methods."
            )

        sandbox_kwargs = map_resource_settings(
            cpu=effective_cpu,
            memory_mb=effective_memory_mb,
            gpu=effective_gpu,
        )
        sandbox_kwargs.update(
            {
                "image": modal_image,
                "timeout": effective_timeout_seconds,
                "app": app,
                "block_network": effective_network_policy.block_network,
            }
        )
        if effective_network_policy.cidr_allowlist is not None:
            sandbox_kwargs["cidr_allowlist"] = (
                effective_network_policy.cidr_allowlist
            )

        try:
            output_context = (
                modal.enable_output()
                if step_settings.verbose
                else nullcontext()
            )
            with output_context:
                sandbox = _call_modal(
                    modal.Sandbox.create,
                    "sleep",
                    "1000000000",
                    **sandbox_kwargs,
                )
                _patch_command_router_fallback(sandbox)
        except Exception:
            _close_modal_context(app_run_context, app_run_context_is_async)
            raise

        session_metadata = SandboxSessionMetadata(
            session_id=str(uuid4()),
            provider=self.flavor,
            network_policy=effective_network_policy,
            tags=effective_tags,
            extra={
                "app_name": self.config.app_name,
                "image": effective_image,
                "cpu": effective_cpu,
                "memory_mb": effective_memory_mb,
                "gpu": effective_gpu,
                "network_policy": effective_network_policy.model_dump(),
                "pricing_url": "https://modal.com/pricing",
            },
        )
        object_id = getattr(sandbox, "object_id", None)
        if object_id:
            session_metadata.extra["object_id"] = str(object_id)

        self._track_session(session_metadata)
        return ModalSandboxSession(
            sandbox,
            app_run_context=app_run_context,
            app_run_context_is_async=app_run_context_is_async,
            raise_on_failure=self.config.raise_on_failure,
            metadata=session_metadata,
            cpu=effective_cpu,
            memory_mb=effective_memory_mb,
            gpu=effective_gpu,
            cpu_cost_per_core_second_usd=(
                self.config.cpu_cost_per_core_second_usd
            ),
            memory_cost_per_gib_second_usd=(
                self.config.memory_cost_per_gib_second_usd
            ),
            env=effective_env,
            workdir=workdir,
        )
