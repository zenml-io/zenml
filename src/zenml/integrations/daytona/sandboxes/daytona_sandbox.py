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
"""Daytona sandbox implementation."""

import importlib
import inspect
import json
import math
import queue
import shlex
import tempfile
import threading
import time
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
    cast,
)
from uuid import uuid4

from zenml.client import Client
from zenml.integrations.daytona.flavors import (
    DaytonaSandboxConfig,
    DaytonaSandboxSettings,
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

_DEFAULT_TIMEOUT_SECONDS = 300
_STREAM_POLL_INTERVAL_SECONDS = 0.25
_ACTIVITY_REFRESH_INTERVAL_SECONDS = 30.0


def _get_attr(obj: Any, names: Sequence[str], default: Any = None) -> Any:
    """Gets the first matching attribute or dictionary key from an object."""
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]

        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def _as_text(value: Any) -> str:
    """Normalizes a value to UTF-8 text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_bytes(value: Any) -> bytes:
    """Normalizes a value to bytes."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return _as_text(value).encode("utf-8")


def _extract_exit_code(value: Any) -> Optional[int]:
    """Extracts an exit code from an SDK response object."""
    raw_code = _get_attr(
        value,
        ["exit_code", "exitCode", "returncode", "return_code", "code"],
        None,
    )
    if raw_code is None:
        return None

    try:
        return int(raw_code)
    except (TypeError, ValueError):
        return None


def _extract_command_id(value: Any) -> Optional[str]:
    """Extracts a session command identifier from an SDK response object."""
    raw_id = _get_attr(value, ["cmd_id", "command_id", "id"], None)
    if raw_id is None:
        return None
    return str(raw_id)


def _extract_output(value: Any) -> Optional[Any]:
    """Extracts structured output from an SDK response object."""
    return _get_attr(value, ["output"], None)


def _extract_stdout_stderr(value: Any) -> tuple[str, str]:
    """Extracts stdout/stderr text from an SDK response object."""
    stdout = _as_text(_get_attr(value, ["stdout", "result", "output"], ""))
    stderr = _as_text(
        _get_attr(value, ["stderr", "error", "error_output"], "")
    )
    return stdout, stderr


def _split_lines(text: str) -> List[str]:
    """Splits text into newline-preserving chunks."""
    if not text:
        return []

    lines = text.splitlines(keepends=True)
    if lines:
        return lines

    return [text]


def _prepare_python_code(code: str, inputs: Optional[Dict[str, Any]]) -> str:
    """Injects input variables into Python code in a provider-agnostic way."""
    if not inputs:
        return code

    serialized_inputs = json.dumps(inputs)
    return (
        "import json\n"
        f"_zenml_inputs = json.loads({serialized_inputs!r})\n"
        "globals().update(_zenml_inputs)\n"
        f"{code}"
    )


def _shell_join(command: List[str]) -> str:
    """Joins argv into a shell-safe command string."""
    return shlex.join(command)


def _call_with_supported_kwargs(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Calls a function, dropping unsupported keyword arguments when possible."""
    if not kwargs:
        return func(*args)

    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return func(*args, **kwargs)

    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return func(*args, **kwargs)

    filtered_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }
    return func(*args, **filtered_kwargs)


def _call_first(
    obj: Any,
    method_names: Sequence[str],
    *,
    args: Sequence[Any] = (),
    kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    """Calls the first available method from a list of method names."""
    kwargs = kwargs or {}
    errors: List[Exception] = []

    for name in method_names:
        method = getattr(obj, name, None)
        if not callable(method):
            continue

        try:
            return _call_with_supported_kwargs(method, *args, **kwargs)
        except (TypeError, ValueError) as e:
            errors.append(e)

    if errors:
        raise errors[-1]

    raise AttributeError(
        f"None of methods {method_names} are available on {type(obj).__name__}."
    )


def _import_daytona_module() -> Any:
    """Imports a Daytona SDK module from known package names."""
    import_errors: List[ImportError] = []

    for module_name in ("daytona", "daytona_sdk"):
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            import_errors.append(e)

    raise ImportError(
        "Could not import Daytona SDK. Install it with "
        "`zenml integration install daytona` and verify your environment."
    ) from (import_errors[-1] if import_errors else None)


def _resolve_daytona_class(
    daytona_module: Any, class_names: Sequence[str]
) -> Optional[Any]:
    """Resolves the first available class from the Daytona module."""
    for class_name in class_names:
        cls = getattr(daytona_module, class_name, None)
        if cls is not None:
            return cls

    return None


def _create_daytona_client(daytona_module: Any, api_url: Optional[str]) -> Any:
    """Creates a Daytona client instance with optional API endpoint override."""
    daytona_class = _resolve_daytona_class(daytona_module, ["Daytona"])
    if daytona_class is None:
        raise RuntimeError("Daytona SDK does not expose a `Daytona` client.")

    if not api_url:
        return daytona_class()

    daytona_config_class = _resolve_daytona_class(
        daytona_module, ["DaytonaConfig"]
    )
    if daytona_config_class is not None:
        for config_kwargs in (
            {"api_url": api_url},
            {"server_url": api_url},
        ):
            try:
                config = _instantiate_dataclass_like(
                    daytona_config_class, config_kwargs
                )
                configured_url = _as_text(
                    _get_attr(config, ["api_url", "server_url"], "")
                )
                if configured_url == api_url:
                    return daytona_class(config=config)
            except Exception:
                logger.debug(
                    "Failed to initialize DaytonaConfig with kwargs %s.",
                    config_kwargs,
                    exc_info=True,
                )

    try:
        constructor_signature = inspect.signature(daytona_class)
    except (TypeError, ValueError):
        constructor_signature = None

    has_var_kwargs = constructor_signature is not None and any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in constructor_signature.parameters.values()
    )

    candidate_kwargs = [
        {"api_url": api_url},
        {"server_url": api_url},
        {"base_url": api_url},
        {"apiUrl": api_url},
    ]
    for kwargs in candidate_kwargs:
        if constructor_signature is not None and not has_var_kwargs:
            if not set(kwargs).issubset(constructor_signature.parameters):
                continue

        try:
            return daytona_class(**kwargs)
        except TypeError:
            continue

    logger.debug(
        "Daytona client constructor does not expose an API URL argument. "
        "Falling back to default constructor."
    )
    return daytona_class()


def _instantiate_dataclass_like(cls: Any, kwargs: Dict[str, Any]) -> Any:
    """Instantiates dataclass-like SDK objects with compatible keyword args."""
    return _call_with_supported_kwargs(cls, **kwargs)


def _build_resources(
    daytona_module: Any,
    *,
    cpu: Optional[int],
    memory_gb: Optional[int],
    disk_gb: Optional[int],
    gpu: Optional[int],
) -> Optional[Any]:
    """Creates a Daytona `Resources` object when available."""
    resources_kwargs: Dict[str, Any] = {}
    if cpu is not None:
        resources_kwargs["cpu"] = cpu
    if memory_gb is not None:
        resources_kwargs["memory"] = memory_gb
    if disk_gb is not None:
        resources_kwargs["disk"] = disk_gb
    if gpu is not None:
        resources_kwargs["gpu"] = gpu

    if not resources_kwargs:
        return None

    resources_class = _resolve_daytona_class(daytona_module, ["Resources"])
    if resources_class is None:
        return resources_kwargs

    return _instantiate_dataclass_like(resources_class, resources_kwargs)


def _create_sandbox(
    daytona_client: Any,
    daytona_module: Any,
    create_kwargs: Dict[str, Any],
) -> Any:
    """Creates a Daytona sandbox while handling SDK shape differences."""
    create_method = getattr(daytona_client, "create", None)
    if not callable(create_method):
        raise RuntimeError("Daytona client does not support sandbox creation.")

    params_classes = [
        _resolve_daytona_class(
            daytona_module, ["CreateSandboxFromImageParams"]
        ),
        _resolve_daytona_class(
            daytona_module, ["CreateSandboxFromSnapshotParams"]
        ),
    ]

    requires_explicit_image = bool(create_kwargs.get("image"))

    for params_class in params_classes:
        if params_class is None:
            continue

        if requires_explicit_image and "Snapshot" in getattr(
            params_class, "__name__", ""
        ):
            continue

        try:
            params = _instantiate_dataclass_like(params_class, create_kwargs)
            if (
                requires_explicit_image
                and _get_attr(params, ["image"], None) is None
            ):
                raise RuntimeError(
                    "Daytona image-based sandbox params rejected the `image` "
                    "argument."
                )
            return create_method(params)
        except Exception:
            logger.debug(
                "Failed to create Daytona sandbox using `%s` params.",
                params_class,
                exc_info=True,
            )

    try:
        create_signature = inspect.signature(create_method)
    except (TypeError, ValueError):
        create_signature = None

    if create_signature is not None:
        has_var_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in create_signature.parameters.values()
        )
        if not has_var_kwargs:
            supported_kwargs = {
                key: value
                for key, value in create_kwargs.items()
                if key in create_signature.parameters
            }
            dropped_keys = sorted(set(create_kwargs) - set(supported_kwargs))
            if dropped_keys:
                raise RuntimeError(
                    "Daytona client.create() does not accept these sandbox "
                    f"parameters: {', '.join(dropped_keys)}."
                )
            return create_method(**supported_kwargs)

    try:
        return create_method(**create_kwargs)
    except Exception as e:
        logger.debug(
            "Failed to create Daytona sandbox with keyword args.",
            exc_info=True,
        )
        raise RuntimeError(
            "Failed to create Daytona sandbox with the configured parameters. "
            "Check Daytona SDK compatibility and provided sandbox settings."
        ) from e


def _extract_message_output(message: Any) -> str:
    """Extracts log text from Daytona output callback messages."""
    if isinstance(message, str):
        return message
    if isinstance(message, bytes):
        return message.decode("utf-8", errors="replace")
    return _as_text(_get_attr(message, ["output", "message", "text"], message))


def _resolve_auto_stop_interval(timeout_seconds: int) -> int:
    """Computes a safe auto-stop interval for long-running sessions."""
    return max(15, math.ceil(timeout_seconds / 60) + 5)


def _parse_gpu_count(gpu: Optional[str]) -> Optional[int]:
    """Parses Daytona GPU count from a generic ZenML GPU setting."""
    if gpu is None:
        return None

    try:
        return int(float(gpu))
    except (TypeError, ValueError):
        return None


def _is_sdk_shape_error(error: Exception) -> bool:
    """Checks if an exception likely indicates SDK signature drift."""
    return isinstance(error, (AttributeError, TypeError, ValueError))


class _BufferedDaytonaProcess(SandboxProcess):
    """Fallback process handle backed by an already-collected command result."""

    def __init__(
        self,
        *,
        result: SandboxExecResult,
        terminate_session: Any,
    ) -> None:
        """Initializes the buffered process wrapper.

        Args:
            result: Collected command result.
            terminate_session: Session termination callback.
        """
        self._result = result
        self._terminate_session = terminate_session

    def stdout_iter(self) -> Iterator[str]:
        """Iterates over buffered stdout lines."""
        for line in _split_lines(self._result.stdout):
            logger.info("[sandbox:stdout] %s", line.rstrip("\n"))
            yield line

    def stderr_iter(self) -> Iterator[str]:
        """Iterates over buffered stderr lines."""
        for line in _split_lines(self._result.stderr):
            logger.warning("[sandbox:stderr] %s", line.rstrip("\n"))
            yield line

    def wait(self, timeout_seconds: Optional[int] = None) -> int:
        """Returns the already-known exit code."""
        _ = timeout_seconds
        return self._result.exit_code

    @property
    def exit_code(self) -> Optional[int]:
        """Returns the buffered process exit code."""
        return self._result.exit_code

    def kill(self) -> None:
        """Cancels process execution by terminating the entire session."""
        self._terminate_session(reason="process kill requested")


class DaytonaSandboxProcess(SandboxProcess):
    """Streaming process wrapper backed by Daytona process sessions."""

    def __init__(
        self,
        session: "DaytonaSandboxSession",
        session_id: str,
        command_id: Optional[str],
    ) -> None:
        """Initializes a streaming process handle.

        Args:
            session: Parent sandbox session.
            session_id: Daytona process session ID.
            command_id: Daytona command ID for log retrieval.
        """
        self._session = session
        self._session_id = session_id
        self._command_id = command_id

        self._stdout_queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._stderr_queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._done_event = threading.Event()
        self._stop_event = threading.Event()
        self._cached_exit_code: Optional[int] = None

        self._stdout_offset = 0
        self._stderr_offset = 0

        self._poll_thread = threading.Thread(
            target=self._poll,
            name=f"daytona-stream-{session_id}",
            daemon=True,
        )
        self._poll_thread.start()

    def _enqueue_delta(
        self,
        text: str,
        *,
        previous_offset: int,
        output_queue: "queue.Queue[Optional[str]]",
    ) -> int:
        """Enqueues unseen log chunks and returns the new offset."""
        if not text:
            return previous_offset

        normalized = _as_text(text)
        if previous_offset > len(normalized):
            previous_offset = 0

        unseen = normalized[previous_offset:]
        for line in _split_lines(unseen):
            output_queue.put(line)

        return len(normalized)

    def _poll(self) -> None:
        """Background poll loop for logs and completion state."""
        try:
            while not self._stop_event.is_set():
                stdout, stderr = self._session._get_session_command_logs(
                    session_id=self._session_id,
                    command_id=self._command_id,
                )
                self._stdout_offset = self._enqueue_delta(
                    stdout,
                    previous_offset=self._stdout_offset,
                    output_queue=self._stdout_queue,
                )
                self._stderr_offset = self._enqueue_delta(
                    stderr,
                    previous_offset=self._stderr_offset,
                    output_queue=self._stderr_queue,
                )

                exit_code = self._session._get_command_exit_code(
                    session_id=self._session_id,
                    command_id=self._command_id,
                )
                if exit_code is not None:
                    self._cached_exit_code = exit_code
                    break

                self._session._refresh_activity()
                time.sleep(_STREAM_POLL_INTERVAL_SECONDS)
        except Exception:
            logger.debug(
                "Daytona streaming poll loop failed for session `%s`.",
                self._session_id,
                exc_info=True,
            )
            if self._cached_exit_code is None:
                self._cached_exit_code = -1
        finally:
            self._done_event.set()
            self._stdout_queue.put(None)
            self._stderr_queue.put(None)
            self._session._delete_process_session(self._session_id)

    def _iter_queue(
        self, output_queue: "queue.Queue[Optional[str]]", *, stderr: bool
    ) -> Iterator[str]:
        """Yields lines from an internal stream queue."""
        while True:
            try:
                line = output_queue.get(timeout=0.1)
            except queue.Empty:
                if self._done_event.is_set():
                    break
                continue

            if line is None:
                break

            if stderr:
                logger.warning("[sandbox:stderr] %s", line.rstrip("\n"))
            else:
                logger.info("[sandbox:stdout] %s", line.rstrip("\n"))
            yield line

    def stdout_iter(self) -> Iterator[str]:
        """Iterates over stdout lines as they arrive."""
        yield from self._iter_queue(self._stdout_queue, stderr=False)

    def stderr_iter(self) -> Iterator[str]:
        """Iterates over stderr lines as they arrive."""
        yield from self._iter_queue(self._stderr_queue, stderr=True)

    def wait(self, timeout_seconds: Optional[int] = None) -> int:
        """Waits for process completion and returns its exit code."""
        if timeout_seconds is None:
            while not self._done_event.wait(timeout=1.0):
                self._session._refresh_activity()
        else:
            deadline = time.monotonic() + timeout_seconds
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return -1
                if self._done_event.wait(timeout=min(1.0, remaining)):
                    break
                self._session._refresh_activity()

        if self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)

        if self._cached_exit_code is None:
            return -1

        return self._cached_exit_code

    @property
    def exit_code(self) -> Optional[int]:
        """Returns the process exit code when available."""
        return self._cached_exit_code

    def kill(self) -> None:
        """Attempts to stop the process by deleting its Daytona session."""
        self._stop_event.set()
        self._session._delete_process_session(self._session_id)
        self._cached_exit_code = -1
        self._done_event.set()


class DaytonaCodeInterpreter(CodeInterpreter):
    """Persistent Python interpreter running inside a Daytona sandbox."""

    def __init__(
        self,
        session: "DaytonaSandboxSession",
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """Initializes the interpreter wrapper.

        Args:
            session: Parent sandbox session.
            timeout_seconds: Optional timeout for interpreter commands.
        """
        self._session = session
        self._timeout_seconds = timeout_seconds
        self._context: Optional[Any] = None

    def __enter__(self) -> "DaytonaCodeInterpreter":
        """Creates a new Daytona code interpreter context."""
        interpreter = getattr(self._session._sandbox, "code_interpreter", None)
        if interpreter is None:
            raise RuntimeError(
                "Daytona sandbox does not expose a `code_interpreter` API."
            )

        self._context = _call_first(
            interpreter,
            ["create_context", "createContext"],
        )
        return self

    def run(
        self,
        code: str,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> SandboxExecResult:
        """Executes code in the persistent Daytona interpreter context."""
        if self._context is None:
            self.__enter__()

        interpreter = getattr(self._session._sandbox, "code_interpreter", None)
        if interpreter is None:
            raise RuntimeError(
                "Daytona sandbox does not expose a `code_interpreter` API."
            )

        prepared_code = _prepare_python_code(code, inputs)
        effective_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self._timeout_seconds
        )

        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []

        def _on_stdout(message: Any) -> None:
            stdout_chunks.append(_extract_message_output(message))

        def _on_stderr(message: Any) -> None:
            stderr_chunks.append(_extract_message_output(message))

        call_kwargs: Dict[str, Any] = {
            "context": self._context,
            "on_stdout": _on_stdout,
            "on_stderr": _on_stderr,
        }
        if effective_timeout is not None:
            call_kwargs["timeout"] = effective_timeout

        response: Any = None
        attempts: List[Dict[str, Any]] = [
            call_kwargs,
            {
                key: value
                for key, value in call_kwargs.items()
                if key != "on_stderr"
            },
            {
                key: value
                for key, value in call_kwargs.items()
                if key not in {"on_stdout", "on_stderr"}
            },
        ]

        for kwargs in attempts:
            try:
                response = _call_first(
                    interpreter,
                    ["run_code", "runCode"],
                    args=(prepared_code,),
                    kwargs=kwargs,
                )
                break
            except TypeError:
                continue

        if response is None:
            raise RuntimeError(
                "Failed to execute Daytona code interpreter run."
            )

        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)

        response_stdout, response_stderr = _extract_stdout_stderr(response)
        if not stdout:
            stdout = response_stdout
        if not stderr:
            stderr = response_stderr

        exit_code = _extract_exit_code(response)
        if exit_code is None:
            exit_code = 1 if stderr else 0

        result = SandboxExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            output=_extract_output(response),
        )

        if self._session.raise_on_failure and result.exit_code != 0:
            raise SandboxExecError(result)

        return result

    def __exit__(self, *args: Any) -> None:
        """Deletes the interpreter context."""
        if self._context is None:
            return

        interpreter = getattr(self._session._sandbox, "code_interpreter", None)
        if interpreter is not None:
            try:
                _call_first(
                    interpreter,
                    ["delete_context", "deleteContext"],
                    args=(self._context,),
                )
            except Exception:
                logger.debug(
                    "Failed to delete Daytona interpreter context.",
                    exc_info=True,
                )

        self._context = None


class DaytonaSandboxSession(SandboxSession):
    """Wraps a Daytona sandbox handle as a ZenML SandboxSession."""

    def __init__(
        self,
        sandbox: Any,
        *,
        daytona_module: Any,
        raise_on_failure: bool,
        metadata: SandboxSessionMetadata,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes a sandbox session wrapper.

        Args:
            sandbox: Underlying Daytona sandbox handle.
            daytona_module: Imported Daytona SDK module.
            raise_on_failure: Default failure mode for command execution.
            metadata: Metadata object tracked by the component.
            env: Default environment variables for command execution.
            workdir: Default working directory for command execution.
            timeout_seconds: Default timeout for command execution.
        """
        self._sandbox = sandbox
        self._daytona_module = daytona_module
        self._raise_on_failure = raise_on_failure
        self._metadata = metadata
        self._default_env = dict(env or {})
        self._default_workdir = workdir
        self._default_timeout_seconds = timeout_seconds

        self._created_at = time.monotonic()
        self._terminated = False
        self._process_sessions: Set[str] = set()
        self._last_activity_refresh = 0.0

    @property
    def raise_on_failure(self) -> bool:
        """Returns default failure behavior for this session."""
        return self._raise_on_failure

    def _process_api(self) -> Any:
        """Returns the Daytona process API handle."""
        process_api = getattr(self._sandbox, "process", None)
        if process_api is None:
            raise RuntimeError(
                "Daytona sandbox does not expose `process` API."
            )
        return process_api

    def _filesystem_api(self) -> Any:
        """Returns the Daytona filesystem API handle."""
        fs_api = getattr(self._sandbox, "fs", None)
        if fs_api is None:
            raise RuntimeError("Daytona sandbox does not expose `fs` API.")
        return fs_api

    def _effective_timeout(self, timeout_seconds: Optional[int]) -> int:
        """Resolves an operation timeout value."""
        if timeout_seconds is None:
            return self._default_timeout_seconds
        return timeout_seconds

    def _effective_workdir(self, workdir: Optional[str]) -> Optional[str]:
        """Resolves the working directory for command execution."""
        if workdir is not None:
            return workdir
        return self._default_workdir

    def _effective_env(self, env: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Resolves environment variables for command execution."""
        effective_env = dict(self._default_env)
        if env:
            effective_env.update(env)
        return effective_env

    def _refresh_activity(self) -> None:
        """Refreshes Daytona activity to avoid inactivity auto-stop."""
        now = time.monotonic()
        if (
            now - self._last_activity_refresh
            < _ACTIVITY_REFRESH_INTERVAL_SECONDS
        ):
            return

        refresh_method = getattr(self._sandbox, "refresh_activity", None)
        if callable(refresh_method):
            try:
                _call_with_supported_kwargs(refresh_method)
            except Exception:
                logger.debug(
                    "Failed to refresh Daytona sandbox activity.",
                    exc_info=True,
                )

        self._last_activity_refresh = now

    def _create_process_session(self, session_id: str) -> None:
        """Creates a Daytona process session and tracks its ID."""
        process_api = self._process_api()
        _call_first(process_api, ["create_session"], args=(session_id,))
        self._process_sessions.add(session_id)

    def _delete_process_session(self, session_id: str) -> None:
        """Deletes a Daytona process session if it still exists."""
        if session_id not in self._process_sessions:
            return

        process_api = self._process_api()
        delete_method = getattr(process_api, "delete_session", None)
        if callable(delete_method):
            try:
                _call_with_supported_kwargs(delete_method, session_id)
            except Exception:
                logger.debug(
                    "Failed to delete Daytona process session `%s`.",
                    session_id,
                    exc_info=True,
                )

        self._process_sessions.discard(session_id)

    def _wait_for_command_exit_code(
        self,
        *,
        session_id: str,
        command_id: Optional[str],
        timeout_seconds: Optional[int],
    ) -> int:
        """Waits for a session command to finish and returns its exit code."""
        deadline = (
            None
            if timeout_seconds is None
            else time.monotonic() + timeout_seconds
        )

        while True:
            exit_code = self._get_command_exit_code(
                session_id=session_id,
                command_id=command_id,
            )
            if exit_code is not None:
                return exit_code

            if deadline is not None and time.monotonic() >= deadline:
                return -1

            self._refresh_activity()
            time.sleep(_STREAM_POLL_INTERVAL_SECONDS)

    def _get_command_exit_code(
        self, *, session_id: str, command_id: Optional[str]
    ) -> Optional[int]:
        """Reads the latest exit code for a process session command."""
        process_api = self._process_api()
        session = _call_first(process_api, ["get_session"], args=(session_id,))

        commands = _get_attr(session, ["commands"], [])
        if not isinstance(commands, list):
            commands = []

        if command_id:
            for command in commands:
                candidate_id = _extract_command_id(command)
                if candidate_id == command_id:
                    return _extract_exit_code(command)

        if len(commands) == 1:
            return _extract_exit_code(commands[0])

        return _extract_exit_code(session)

    def _get_session_command_logs(
        self,
        *,
        session_id: str,
        command_id: Optional[str],
    ) -> tuple[str, str]:
        """Fetches process-session command logs."""
        process_api = self._process_api()

        resolved_command_id = command_id
        if resolved_command_id is None:
            session = _call_first(
                process_api, ["get_session"], args=(session_id,)
            )
            commands = _get_attr(session, ["commands"], [])
            if isinstance(commands, list) and len(commands) == 1:
                resolved_command_id = _extract_command_id(commands[0])

        if resolved_command_id is None:
            return "", ""

        logs = _call_first(
            process_api,
            ["get_session_command_logs"],
            args=(session_id, resolved_command_id),
        )

        return _extract_stdout_stderr(logs)

    def _build_session_execute_requests(
        self,
        *,
        command: str,
        run_async: bool,
        timeout_seconds: Optional[int],
        env: Dict[str, str],
        workdir: Optional[str],
    ) -> List[Any]:
        """Builds request payload variants for session command execution."""
        request_payload: Dict[str, Any] = {"command": command}
        if workdir:
            request_payload["cwd"] = workdir
        if timeout_seconds is not None:
            request_payload["timeout"] = timeout_seconds
        if env:
            request_payload["env"] = env

        request_class = _resolve_daytona_class(
            self._daytona_module, ["SessionExecuteRequest"]
        )

        requests: List[Any] = []
        for async_key in ("run_async", "var_async"):
            payload = dict(request_payload)
            payload[async_key] = run_async

            if request_class is not None:
                try:
                    requests.append(
                        _instantiate_dataclass_like(request_class, payload)
                    )
                    continue
                except Exception:
                    logger.debug(
                        "Failed to instantiate SessionExecuteRequest with `%s`.",
                        async_key,
                        exc_info=True,
                    )

            requests.append(payload)

        return requests

    def _execute_session_command(
        self,
        command: List[str],
        *,
        run_async: bool,
        timeout_seconds: Optional[int],
        env: Optional[Dict[str, str]],
        workdir: Optional[str],
    ) -> tuple[str, Optional[str], Any]:
        """Executes a command using Daytona process sessions."""
        if not command:
            raise ValueError("Cannot execute an empty command in a sandbox.")

        process_api = self._process_api()
        session_id = f"zenml-{uuid4().hex[:12]}"
        self._create_process_session(session_id)

        command_text = _shell_join(command)
        effective_env = self._effective_env(env)
        effective_timeout = self._effective_timeout(timeout_seconds)
        effective_workdir = self._effective_workdir(workdir)

        requests = self._build_session_execute_requests(
            command=command_text,
            run_async=run_async,
            timeout_seconds=effective_timeout,
            env=effective_env,
            workdir=effective_workdir,
        )

        errors: List[Exception] = []
        for request in requests:
            try:
                response = _call_first(
                    process_api,
                    ["execute_session_command"],
                    args=(session_id, request),
                )
                return session_id, _extract_command_id(response), response
            except Exception as e:
                errors.append(e)

                if not _is_sdk_shape_error(e):
                    self._delete_process_session(session_id)
                    raise

                if isinstance(request, dict):
                    try:
                        response = _call_first(
                            process_api,
                            ["execute_session_command"],
                            args=(session_id,),
                            kwargs=request,
                        )
                        return (
                            session_id,
                            _extract_command_id(response),
                            response,
                        )
                    except Exception as nested_exception:
                        errors.append(nested_exception)
                        if not _is_sdk_shape_error(nested_exception):
                            self._delete_process_session(session_id)
                            raise

        self._delete_process_session(session_id)

        if errors:
            raise errors[-1]

        raise RuntimeError("Failed to execute Daytona session command.")

    def _exec_run_fallback(
        self,
        command: List[str],
        *,
        timeout_seconds: Optional[int],
        env: Optional[Dict[str, str]],
        workdir: Optional[str],
    ) -> SandboxExecResult:
        """Fallback command execution using `process.exec`."""
        process_api = self._process_api()

        command_text = _shell_join(command)
        kwargs: Dict[str, Any] = {}

        effective_timeout = self._effective_timeout(timeout_seconds)
        kwargs["timeout"] = effective_timeout

        effective_env = self._effective_env(env)
        if effective_env:
            kwargs["env"] = effective_env

        effective_workdir = self._effective_workdir(workdir)
        if effective_workdir:
            kwargs["cwd"] = effective_workdir

        response = _call_first(
            process_api,
            ["exec", "execute"],
            args=(command_text,),
            kwargs=kwargs,
        )

        stdout, stderr = _extract_stdout_stderr(response)
        exit_code = _extract_exit_code(response)
        if exit_code is None:
            exit_code = 1 if stderr else 0

        return SandboxExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            output=_extract_output(response),
        )

    def _finalize_metadata(self) -> None:
        """Finalizes metadata tracked by the sandbox session."""
        self._metadata.duration_seconds = max(
            self._metadata.duration_seconds,
            time.monotonic() - self._created_at,
        )
        self._metadata.extra.setdefault(
            "estimated_cost_reason", "not available in daytona provider v1"
        )

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
        session_id: Optional[str] = None
        daytona_error_class = _resolve_daytona_class(
            self._daytona_module, ["DaytonaError"]
        )

        try:
            session_id, command_id, response = self._execute_session_command(
                command,
                run_async=False,
                timeout_seconds=timeout_seconds,
                env=env,
                workdir=workdir,
            )
        except Exception as e:
            if daytona_error_class and isinstance(e, daytona_error_class):
                result = SandboxExecResult(
                    exit_code=1,
                    stdout="",
                    stderr=_as_text(e),
                )
            elif _is_sdk_shape_error(e):
                logger.debug(
                    "Failed to execute Daytona command via session APIs due "
                    "to SDK shape mismatch. Falling back to process.exec.",
                    exc_info=True,
                )
                result = self._exec_run_fallback(
                    command,
                    timeout_seconds=timeout_seconds,
                    env=env,
                    workdir=workdir,
                )
            else:
                raise
        else:
            stdout, stderr = _extract_stdout_stderr(response)

            try:
                session_stdout, session_stderr = (
                    self._get_session_command_logs(
                        session_id=session_id,
                        command_id=command_id,
                    )
                )
                if session_stdout:
                    stdout = session_stdout
                if session_stderr:
                    stderr = session_stderr
            except Exception as log_error:
                if _is_sdk_shape_error(log_error):
                    logger.debug(
                        "Daytona session log APIs are partially unavailable. "
                        "Using command response output instead.",
                        exc_info=True,
                    )
                else:
                    raise

            exit_code = _extract_exit_code(response)
            if exit_code is None:
                try:
                    exit_code = self._wait_for_command_exit_code(
                        session_id=session_id,
                        command_id=command_id,
                        timeout_seconds=self._effective_timeout(
                            timeout_seconds
                        ),
                    )
                except Exception as wait_error:
                    if _is_sdk_shape_error(wait_error):
                        logger.debug(
                            "Daytona session status APIs are partially "
                            "unavailable. Falling back to output-based exit "
                            "code inference.",
                            exc_info=True,
                        )
                        exit_code = 1 if stderr else 0
                    else:
                        raise

            result = SandboxExecResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                output=_extract_output(response),
            )
        finally:
            if session_id is not None:
                self._delete_process_session(session_id)

        self._metadata.commands_executed += 1

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
        """Runs a command and yields streaming process output."""
        self._metadata.commands_executed += 1

        try:
            session_id, command_id, _ = self._execute_session_command(
                command,
                run_async=True,
                timeout_seconds=timeout_seconds,
                env=env,
                workdir=workdir,
            )
            return DaytonaSandboxProcess(
                session=self,
                session_id=session_id,
                command_id=command_id,
            )
        except Exception as e:
            daytona_error_class = _resolve_daytona_class(
                self._daytona_module, ["DaytonaError"]
            )
            if daytona_error_class and isinstance(e, daytona_error_class):
                return _BufferedDaytonaProcess(
                    result=SandboxExecResult(
                        exit_code=1,
                        stdout="",
                        stderr=_as_text(e),
                    ),
                    terminate_session=self.terminate,
                )

            if not _is_sdk_shape_error(e):
                raise

            logger.debug(
                "Daytona streaming session execution unavailable due to SDK "
                "shape mismatch. Falling back to buffered process output.",
                exc_info=True,
            )
            fallback_result = self._exec_run_fallback(
                command,
                timeout_seconds=timeout_seconds,
                env=env,
                workdir=workdir,
            )
            return _BufferedDaytonaProcess(
                result=fallback_result,
                terminate_session=self.terminate,
            )

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
                "DaytonaSandboxSession.run_code currently only supports "
                "language='python'."
            )

        prepared_code = _prepare_python_code(code, inputs)
        process_api = self._process_api()

        kwargs: Dict[str, Any] = {}
        effective_timeout = self._effective_timeout(timeout_seconds)
        kwargs["timeout"] = effective_timeout

        effective_env = self._effective_env(None)
        if effective_env:
            kwargs["env"] = effective_env

        try:
            response = _call_first(
                process_api,
                ["code_run", "codeRun"],
                args=(prepared_code,),
                kwargs=kwargs,
            )

            stdout, stderr = _extract_stdout_stderr(response)
            exit_code = _extract_exit_code(response)
            if exit_code is None:
                exit_code = 1 if stderr else 0

            result = SandboxExecResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                output=_extract_output(response),
            )
        except Exception as e:
            daytona_error_class = _resolve_daytona_class(
                self._daytona_module, ["DaytonaError"]
            )
            if daytona_error_class and isinstance(e, daytona_error_class):
                result = SandboxExecResult(
                    exit_code=1,
                    stdout="",
                    stderr=_as_text(e),
                )
            elif _is_sdk_shape_error(e):
                logger.debug(
                    "Daytona process.code_run unavailable due to SDK shape "
                    "mismatch; falling back to python -c execution.",
                    exc_info=True,
                )
                result = self._exec_run_fallback(
                    ["python", "-c", prepared_code],
                    timeout_seconds=timeout_seconds,
                    env=None,
                    workdir=None,
                )
            else:
                raise

        self._metadata.commands_executed += 1

        should_check = check if check is not None else self._raise_on_failure
        if should_check and result.exit_code != 0:
            raise SandboxExecError(result)

        return result

    def code_interpreter(self) -> CodeInterpreter:
        """Creates a persistent Python interpreter for repeated execution."""
        return DaytonaCodeInterpreter(self)

    def write_file(self, remote_path: str, content: Union[bytes, str]) -> None:
        """Writes content to a file in the sandbox filesystem."""
        fs_api = self._filesystem_api()

        payload = _as_bytes(content)
        file_upload_class = _resolve_daytona_class(
            self._daytona_module, ["FileUpload"]
        )

        if file_upload_class is not None:
            upload = _instantiate_dataclass_like(
                file_upload_class,
                {
                    "source": payload,
                    "destination": remote_path,
                },
            )
            upload_files = getattr(fs_api, "upload_files", None)
            if callable(upload_files):
                _call_with_supported_kwargs(upload_files, [upload])
                return

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(payload)
            temp_path = Path(temp_file.name)

        try:
            self.upload_file(str(temp_path), remote_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _download_file(
        self, remote_path: str, local_path: Optional[str]
    ) -> Any:
        """Downloads a remote file using the most compatible SDK shape."""
        fs_api = self._filesystem_api()
        download_file = getattr(fs_api, "download_file", None)
        if callable(download_file):
            try:
                if local_path is None:
                    return _call_with_supported_kwargs(
                        download_file, remote_path
                    )

                return _call_with_supported_kwargs(
                    download_file, remote_path, local_path
                )
            except Exception:
                logger.debug(
                    "Direct Daytona fs.download_file call failed.",
                    exc_info=True,
                )

        request_class = _resolve_daytona_class(
            self._daytona_module, ["FileDownloadRequest"]
        )
        if request_class is not None:
            request = _instantiate_dataclass_like(
                request_class,
                {
                    "source": remote_path,
                    "destination": local_path,
                },
            )
            try:
                if callable(download_file):
                    return _call_with_supported_kwargs(download_file, request)
            except Exception:
                logger.debug(
                    "Daytona fs.download_file request-object call failed.",
                    exc_info=True,
                )

            download_files = getattr(fs_api, "download_files", None)
            if callable(download_files):
                return _call_with_supported_kwargs(download_files, [request])

        raise RuntimeError("Failed to download file from Daytona sandbox.")

    def read_file(self, remote_path: str) -> bytes:
        """Reads file content from the sandbox filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "zenml_daytona_download.bin"
            response = self._download_file(remote_path, str(temp_path))
            if temp_path.exists():
                return temp_path.read_bytes()

            if isinstance(response, list) and response:
                response = response[0]

            result = _get_attr(response, ["result"], response)
            if isinstance(result, bytes):
                return result
            if isinstance(result, str):
                path_candidate = Path(result)
                if path_candidate.exists():
                    return path_candidate.read_bytes()
                return result.encode("utf-8")

            raise RuntimeError(
                "Daytona file download did not return readable content."
            )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file to the sandbox filesystem."""
        fs_api = self._filesystem_api()

        upload_file = getattr(fs_api, "upload_file", None)
        if callable(upload_file):
            try:
                _call_with_supported_kwargs(
                    upload_file, local_path, remote_path
                )
                return
            except Exception:
                logger.debug(
                    "Daytona fs.upload_file call failed, retrying with "
                    "upload_files.",
                    exc_info=True,
                )

        file_upload_class = _resolve_daytona_class(
            self._daytona_module, ["FileUpload"]
        )
        upload_files = getattr(fs_api, "upload_files", None)
        if file_upload_class is not None and callable(upload_files):
            upload = _instantiate_dataclass_like(
                file_upload_class,
                {
                    "source": local_path,
                    "destination": remote_path,
                },
            )
            _call_with_supported_kwargs(upload_files, [upload])
            return

        raise RuntimeError("Failed to upload file into Daytona sandbox.")

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a sandbox file to local storage."""
        response = self._download_file(remote_path, local_path)

        local_target = Path(local_path)
        if local_target.exists():
            return

        if isinstance(response, list) and response:
            response = response[0]

        result = _get_attr(response, ["result"], response)
        if isinstance(result, bytes):
            local_target.write_bytes(result)
            return

        if isinstance(result, str):
            source_path = Path(result)
            if source_path.exists():
                local_target.write_bytes(source_path.read_bytes())
                return

        raise RuntimeError(
            "Daytona file download did not produce a local artifact."
        )

    def terminate(self, reason: Optional[str] = None) -> None:
        """Terminates the active sandbox session."""
        if self._terminated:
            return

        if reason:
            logger.debug("Terminating Daytona sandbox session: %s", reason)

        try:
            for session_id in list(self._process_sessions):
                self._delete_process_session(session_id)

            try:
                delete_method = getattr(self._sandbox, "delete", None)
                if callable(delete_method):
                    _call_with_supported_kwargs(delete_method, timeout=60)
                else:
                    stop_method = getattr(self._sandbox, "stop", None)
                    if callable(stop_method):
                        _call_with_supported_kwargs(stop_method, timeout=60)
            except Exception:
                logger.debug(
                    "Failed to finalize Daytona sandbox termination. "
                    "Ignoring cleanup error.",
                    exc_info=True,
                )
        finally:
            self._terminated = True
            self._finalize_metadata()

    def __enter__(self) -> "SandboxSession":
        """Enters the sandbox session context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exits the sandbox session context manager."""
        self.terminate(reason="session context exited")


class DaytonaSandbox(BaseSandbox):
    """Daytona implementation of the ZenML sandbox stack component."""

    @property
    def config(self) -> DaytonaSandboxConfig:
        """Typed Daytona sandbox configuration."""
        return cast(DaytonaSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for step-level sandbox overrides."""
        return DaytonaSandboxSettings

    @property
    def capabilities(self) -> Set[SandboxCapability]:
        """Capabilities supported by the Daytona sandbox provider."""
        return {
            SandboxCapability.FILESYSTEM,
            SandboxCapability.STREAMING_OUTPUT,
            SandboxCapability.PERSISTENT_SESSIONS,
        }

    def _resolve_step_settings(self) -> DaytonaSandboxSettings:
        """Resolves step-level settings if called inside a running step."""
        base_settings = DaytonaSandboxSettings.model_validate(
            self.config.model_dump(exclude_unset=True)
        )

        try:
            from zenml.steps import get_step_context

            step_context = get_step_context()
            return cast(
                DaytonaSandboxSettings,
                self.get_settings(step_context.step_run),
            )
        except RuntimeError:
            return base_settings
        except Exception:
            logger.debug(
                "Failed to resolve Daytona sandbox step settings. Falling "
                "back to component defaults.",
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
        """Creates a Daytona sandbox session and returns its context manager."""
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
                else _DEFAULT_TIMEOUT_SECONDS
            )
        )
        effective_cpu = (
            cpu
            if cpu is not None
            else (
                step_settings.cpu
                if step_settings.cpu is not None
                else float(self.config.default_cpu)
            )
        )
        effective_memory_mb = (
            memory_mb
            if memory_mb is not None
            else (
                step_settings.memory_mb
                if step_settings.memory_mb is not None
                else self.config.default_memory_gb * 1024
            )
        )

        effective_gpu = (
            gpu if gpu is not None else cast(Optional[str], step_settings.gpu)
        )
        parsed_gpu = _parse_gpu_count(effective_gpu)
        if effective_gpu and parsed_gpu is None:
            logger.warning(
                "Ignoring Daytona GPU setting `%s`; DaytonaSandbox currently "
                "accepts numeric GPU counts only.",
                effective_gpu,
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
            effective_network_policy = NetworkPolicy()

        effective_target = (
            step_settings.target
            if step_settings.target is not None
            else self.config.target
        )
        effective_api_url = (
            step_settings.api_url
            if step_settings.api_url is not None
            else self.config.api_url
        )
        effective_ephemeral = step_settings.ephemeral
        effective_auto_stop_interval = (
            step_settings.auto_stop_interval_minutes
            if step_settings.auto_stop_interval_minutes is not None
            else _resolve_auto_stop_interval(effective_timeout_seconds)
        )
        effective_auto_delete_interval = (
            step_settings.auto_delete_interval_minutes
        )

        daytona_module = _import_daytona_module()
        daytona_client = _create_daytona_client(
            daytona_module=daytona_module,
            api_url=effective_api_url,
        )

        resources = _build_resources(
            daytona_module,
            cpu=int(math.ceil(effective_cpu))
            if effective_cpu is not None
            else None,
            memory_gb=math.ceil(effective_memory_mb / 1024)
            if effective_memory_mb is not None
            else None,
            disk_gb=self.config.default_disk_gb,
            gpu=parsed_gpu,
        )

        create_kwargs: Dict[str, Any] = {
            "language": "python",
            "image": effective_image,
            "ephemeral": effective_ephemeral,
            "auto_stop_interval": effective_auto_stop_interval,
        }
        if effective_tags:
            create_kwargs["labels"] = effective_tags
        if effective_env:
            create_kwargs["env"] = effective_env
        if resources is not None:
            create_kwargs["resources"] = resources
        if effective_auto_delete_interval is not None:
            create_kwargs["auto_delete_interval"] = (
                effective_auto_delete_interval
            )
        if effective_target is not None:
            create_kwargs["target"] = effective_target

        if effective_network_policy.block_network:
            create_kwargs["network_block_all"] = True
        if effective_network_policy.cidr_allowlist:
            create_kwargs["network_allow_list"] = ",".join(
                effective_network_policy.cidr_allowlist
            )

        sandbox = _create_sandbox(
            daytona_client=daytona_client,
            daytona_module=daytona_module,
            create_kwargs=create_kwargs,
        )

        sandbox_state = _as_text(_get_attr(sandbox, ["state"], "")).lower()
        start_method = getattr(sandbox, "start", None)
        if callable(start_method):
            should_attempt_start = not sandbox_state or sandbox_state not in {
                "started",
                "running",
            }
            if should_attempt_start:
                try:
                    _call_with_supported_kwargs(start_method, timeout=60)
                except Exception:
                    logger.debug(
                        "Daytona sandbox start call failed; continuing in "
                        "case the sandbox is already active.",
                        exc_info=True,
                    )

        session_metadata = SandboxSessionMetadata(
            session_id=str(uuid4()),
            provider=self.flavor,
            network_policy=effective_network_policy,
            tags=effective_tags,
            extra={
                "image": effective_image,
                "cpu": effective_cpu,
                "memory_mb": effective_memory_mb,
                "disk_gb": self.config.default_disk_gb,
                "gpu": effective_gpu,
                "target": effective_target,
                "api_url": effective_api_url,
                "ephemeral": effective_ephemeral,
                "auto_stop_interval_minutes": effective_auto_stop_interval,
                "auto_delete_interval_minutes": (
                    effective_auto_delete_interval
                ),
                "estimated_cost_reason": "not available in daytona provider v1",
            },
        )

        sandbox_id = _get_attr(sandbox, ["id", "sandbox_id"], None)
        sandbox_name = _get_attr(sandbox, ["name"], None)
        sandbox_url = _get_attr(
            sandbox,
            ["sandbox_url", "url", "dashboard_url", "web_url"],
            None,
        )
        if sandbox_id is not None:
            session_metadata.extra["sandbox_id"] = str(sandbox_id)
        if sandbox_name is not None:
            session_metadata.extra["sandbox_name"] = str(sandbox_name)
        if sandbox_url:
            session_metadata.sandbox_url = str(sandbox_url)

        self._track_session(session_metadata)

        return DaytonaSandboxSession(
            sandbox,
            daytona_module=daytona_module,
            raise_on_failure=self.config.raise_on_failure,
            metadata=session_metadata,
            env=effective_env,
            workdir=workdir,
            timeout_seconds=effective_timeout_seconds,
        )
