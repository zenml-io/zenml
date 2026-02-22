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
"""Monty sandbox implementation."""

import base64
import importlib
import inspect
import json
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    cast,
)
from uuid import uuid4

from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.integrations.monty.flavors import (
    MontySandboxConfig,
    MontySandboxSettings,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    CodeInterpreter,
    JsonSerializable,
    NetworkPolicy,
    SandboxCapability,
    SandboxExecError,
    SandboxExecResult,
    SandboxSession,
    SandboxSessionMetadata,
)

if TYPE_CHECKING:
    from types import ModuleType

logger = get_logger(__name__)

_DEFAULT_SCRIPT_NAME = "zenml_monty_sandbox.py"


def _load_monty_module() -> "ModuleType":
    """Loads the pydantic-monty module lazily.

    Returns:
        Imported `pydantic_monty` module.

    Raises:
        ImportError: If `pydantic_monty` is not installed.
    """
    try:
        return importlib.import_module("pydantic_monty")
    except ImportError as e:
        raise ImportError(
            "Monty sandbox requires the `pydantic-monty` package. Install "
            "it with `zenml integration install monty` or `uv pip install "
            "pydantic-monty`."
        ) from e


def _call_with_supported_kwargs(
    function: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    """Calls a function while filtering unsupported keyword arguments."""
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return function(*args, **kwargs)

    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return function(*args, **kwargs)

    supported_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }
    return function(*args, **supported_kwargs)


def _serialize_output(value: Any) -> Optional[JsonSerializable]:
    """Converts Monty outputs into the sandbox JSON boundary."""
    if value is None:
        return None

    try:
        json.dumps(value)
        return cast(JsonSerializable, value)
    except TypeError:
        return repr(value)


def _format_monty_error(error: BaseException) -> str:
    """Formats Monty errors with rich diagnostics when available."""
    display = getattr(error, "display", None)
    if callable(display):
        for args, kwargs in (
            (("full",), {}),
            ((), {"format": "full"}),
            ((), {}),
        ):
            try:
                rendered = display(*args, **kwargs)
                return str(rendered)
            except TypeError:
                continue
            except Exception:
                break

    return str(error)


def _build_print_callback(
    stdout_chunks: List[str], stderr_chunks: List[str]
) -> Callable[[str, str], None]:
    """Creates a print callback compatible with Monty execution."""

    def _callback(stream: str, text: str) -> None:
        line = str(text)
        if stream == "stderr":
            stderr_chunks.append(line)
            logger.info("[sandbox:stderr] %s", line.rstrip())
            return

        stdout_chunks.append(line)
        logger.info("[sandbox:stdout] %s", line.rstrip())

    return _callback


def _create_os_access(
    monty_module: Any,
    environ: Dict[str, str],
    root_dir: Optional[str],
) -> Optional[Any]:
    """Creates a restricted Monty OS access layer when supported."""
    os_access_class = getattr(monty_module, "OSAccess", None)
    if os_access_class is None:
        return None

    try:
        return _call_with_supported_kwargs(
            os_access_class,
            files=[],
            environ=environ,
            root_dir=root_dir,
        )
    except Exception:
        logger.debug(
            "Failed to initialize Monty OSAccess. Falling back to no OS "
            "callback for this execution.",
            exc_info=True,
        )
        return None


def _render_input_assignments(inputs: Dict[str, Any]) -> str:
    """Renders input values as Python assignments for REPL execution."""
    assignments: List[str] = []
    for name, value in inputs.items():
        if not name.isidentifier():
            raise ValueError(
                f"Input key '{name}' is not a valid Python identifier."
            )
        assignments.append(f"{name} = {value!r}")

    return "\n".join(assignments)


def _merge_type_check_stubs(
    base_stubs: Optional[str], input_names: List[str]
) -> Optional[str]:
    """Merges declared input names into Monty type-checking stubs."""
    valid_inputs = [name for name in input_names if name.isidentifier()]
    if not valid_inputs:
        return base_stubs

    generated = "\n".join(
        ["from typing import Any", *[f"{name}: Any" for name in valid_inputs]]
    )
    if base_stubs:
        return f"{base_stubs.rstrip()}\n\n{generated}"

    return generated


class MontyCodeInterpreter(CodeInterpreter):
    """Persistent code interpreter backed by `pydantic_monty.MontyRepl`."""

    def __init__(
        self,
        session: "MontySandboxSession",
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """Initializes the interpreter.

        Args:
            session: Parent sandbox session.
            timeout_seconds: Optional timeout used to create the interpreter.
        """
        self._session = session
        self._timeout_seconds = timeout_seconds
        self._repl: Optional[Any] = None
        self._stdout_chunks: List[str] = []
        self._stderr_chunks: List[str] = []

    @property
    def has_repl(self) -> bool:
        """Whether a repl instance is currently active."""
        return self._repl is not None

    def _print_callback(self, stream: str, text: str) -> None:
        """Captures Monty print output in sandbox execution results."""
        callback = _build_print_callback(self._stdout_chunks, self._stderr_chunks)
        callback(stream, text)

    def _load_or_create_repl(self) -> Any:
        """Loads a serialized repl state or creates a fresh repl."""
        monty_module = _load_monty_module()
        repl_class = getattr(monty_module, "MontyRepl")

        os_access = self._session._resolve_os_access(env=None, workdir=None)
        limits = self._session._resolve_limits(
            timeout_seconds=self._timeout_seconds
        )

        if self._session.repl_state is not None:
            load_method = getattr(repl_class, "load")
            return _call_with_supported_kwargs(
                load_method,
                self._session.repl_state,
                print_callback=self._print_callback,
                os=os_access,
            )

        create_method = getattr(repl_class, "create")
        created = _call_with_supported_kwargs(
            create_method,
            "",
            script_name=self._session.script_name,
            type_check=self._session.type_check,
            type_check_stubs=self._session.type_check_stubs,
            limits=limits,
            print_callback=self._print_callback,
            os=os_access,
        )
        if isinstance(created, tuple):
            return created[0]
        return created

    def __enter__(self) -> "MontyCodeInterpreter":
        """Starts the interpreter session."""
        if self._session.declared_external_functions:
            raise RuntimeError(
                "Monty code interpreter mode currently does not support "
                "external function declarations. Use run_code() for "
                "external function execution."
            )

        self._repl = self._load_or_create_repl()
        return self

    def run(
        self,
        code: str,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> SandboxExecResult:
        """Executes code while preserving state between calls."""
        if self._repl is None:
            self.__enter__()

        assert self._repl is not None

        if timeout_seconds is not None:
            logger.debug(
                "Ignoring timeout_seconds=%s for Monty code interpreter run; "
                "the REPL uses session-level limits.",
                timeout_seconds,
            )

        self._stdout_chunks = []
        self._stderr_chunks = []

        code_to_run = code
        if inputs:
            prefix = _render_input_assignments(inputs)
            code_to_run = f"{prefix}\n{code}" if prefix else code

        try:
            output = self._repl.feed(code_to_run)
            result = SandboxExecResult(
                exit_code=0,
                stdout="".join(self._stdout_chunks),
                stderr="".join(self._stderr_chunks),
                output=_serialize_output(output),
            )
        except Exception as e:
            if not self._session._is_monty_error(e):
                raise

            formatted_stderr = _format_monty_error(e)
            captured_stderr = "".join(self._stderr_chunks)
            stderr = (
                f"{captured_stderr}\n{formatted_stderr}"
                if captured_stderr
                else formatted_stderr
            )
            result = SandboxExecResult(
                exit_code=1,
                stdout="".join(self._stdout_chunks),
                stderr=stderr,
            )

        self._session._metadata.commands_executed += 1
        self._session._store_repl_state(self.dump_state())

        if self._session.raise_on_failure and result.exit_code != 0:
            raise SandboxExecError(result)

        return result

    def dump_state(self) -> Optional[bytes]:
        """Serializes the active repl state."""
        if self._repl is None:
            return None

        dump_method = getattr(self._repl, "dump", None)
        if not callable(dump_method):
            return None

        dumped = dump_method()
        if isinstance(dumped, bytes):
            return dumped

        return None

    def __exit__(self, *args: Any) -> None:
        """Stops the interpreter session."""
        self._session._store_repl_state(self.dump_state())
        self._repl = None


class MontySandboxSession(SandboxSession):
    """Wraps a Monty runtime handle as a ZenML SandboxSession."""

    def __init__(
        self,
        *,
        raise_on_failure: bool,
        metadata: SandboxSessionMetadata,
        timeout_seconds: int,
        type_check: bool,
        type_check_stubs: Optional[str],
        declared_external_functions: List[str],
        env: Optional[Dict[str, str]],
        workdir: Optional[str],
        memory_mb: Optional[int],
        script_name: str,
    ) -> None:
        """Initializes a Monty sandbox session wrapper."""
        self._raise_on_failure = raise_on_failure
        self._metadata = metadata
        self._default_env = dict(env or {})
        self._workdir = workdir
        self._type_check = type_check
        self._type_check_stubs = type_check_stubs
        self._declared_external_functions = list(declared_external_functions)
        self._script_name = script_name
        self._created_at = time.monotonic()
        self._terminated = False
        self._repl_state: Optional[bytes] = None
        self._active_interpreter: Optional[MontyCodeInterpreter] = None

        self._base_limits: Dict[str, Any] = {}
        if timeout_seconds > 0:
            self._base_limits["max_duration_secs"] = float(timeout_seconds)
        if memory_mb is not None and memory_mb > 0:
            self._base_limits["max_memory"] = int(memory_mb * 1024 * 1024)

        self._metadata.extra["limits"] = dict(self._base_limits)

    @property
    def raise_on_failure(self) -> bool:
        """Returns default failure behavior for this session."""
        return self._raise_on_failure

    @property
    def script_name(self) -> str:
        """Returns the script name passed to Monty for diagnostics."""
        return self._script_name

    @property
    def type_check(self) -> bool:
        """Returns whether Monty type checking is enabled for this session."""
        return self._type_check

    @property
    def type_check_stubs(self) -> Optional[str]:
        """Returns type checking stubs configured for this session."""
        return self._type_check_stubs

    @property
    def declared_external_functions(self) -> List[str]:
        """Returns declared external function names."""
        return list(self._declared_external_functions)

    @property
    def repl_state(self) -> Optional[bytes]:
        """Returns serialized repl state if available."""
        return self._repl_state

    def _is_monty_error(self, error: BaseException) -> bool:
        """Checks whether an exception is a Monty execution failure."""
        monty_module = _load_monty_module()
        monty_error_class = getattr(monty_module, "MontyError", Exception)
        return isinstance(error, monty_error_class)

    def _resolve_limits(
        self, timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Builds effective resource limits for a Monty execution."""
        limits = dict(self._base_limits)
        if timeout_seconds is not None and timeout_seconds > 0:
            limits["max_duration_secs"] = float(timeout_seconds)
        return limits

    def _resolve_os_access(
        self,
        env: Optional[Dict[str, str]],
        workdir: Optional[str],
    ) -> Optional[Any]:
        """Builds a per-call OSAccess instance for controlled env access."""
        monty_module = _load_monty_module()
        merged_env = dict(self._default_env)
        if env:
            merged_env.update(env)

        resolved_workdir = workdir if workdir is not None else self._workdir
        return _create_os_access(
            monty_module,
            merged_env,
            resolved_workdir or "/",
        )

    def _run_monty_code(
        self,
        *,
        code: str,
        inputs: Optional[Dict[str, Any]],
        timeout_seconds: Optional[int],
        env: Optional[Dict[str, str]],
        workdir: Optional[str],
        check: Optional[bool],
    ) -> SandboxExecResult:
        """Executes code with Monty and maps results to SandboxExecResult."""
        monty_module = _load_monty_module()
        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []
        print_callback = _build_print_callback(stdout_chunks, stderr_chunks)

        safe_inputs = dict(inputs or {})
        type_check_stubs = _merge_type_check_stubs(
            self._type_check_stubs,
            list(safe_inputs.keys()),
        )

        monty_instance = _call_with_supported_kwargs(
            getattr(monty_module, "Monty"),
            code,
            inputs=list(safe_inputs.keys()),
            external_functions=self._declared_external_functions,
            script_name=self._script_name,
            type_check=self._type_check,
            type_check_stubs=type_check_stubs,
        )

        run_kwargs: Dict[str, Any] = {
            "limits": self._resolve_limits(timeout_seconds=timeout_seconds),
            "print_callback": print_callback,
            "os": self._resolve_os_access(env=env, workdir=workdir),
        }
        if safe_inputs:
            run_kwargs["inputs"] = safe_inputs

        try:
            output = _call_with_supported_kwargs(
                getattr(monty_instance, "run"),
                **run_kwargs,
            )
            result = SandboxExecResult(
                exit_code=0,
                stdout="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
                output=_serialize_output(output),
            )
        except Exception as e:
            if not self._is_monty_error(e):
                raise

            formatted_stderr = _format_monty_error(e)
            captured_stderr = "".join(stderr_chunks)
            stderr = (
                f"{captured_stderr}\n{formatted_stderr}"
                if captured_stderr
                else formatted_stderr
            )
            result = SandboxExecResult(
                exit_code=1,
                stdout="".join(stdout_chunks),
                stderr=stderr,
                output=None,
            )

        self._metadata.commands_executed += 1
        should_check = check if check is not None else self._raise_on_failure
        if should_check and result.exit_code != 0:
            raise SandboxExecError(result)

        return result

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
        if not command:
            raise ValueError("Cannot execute an empty command in a sandbox.")

        if len(command) >= 3 and command[0] == "python" and command[1] == "-c":
            code = command[2]
        elif len(command) == 1:
            code = command[0]
        else:
            code = command[-1]
            logger.debug(
                "Monty exec_run maps command input to Python code by using "
                "the last argument. Ignored command prefix: %s",
                command[:-1],
            )

        return self._run_monty_code(
            code=code,
            inputs=None,
            timeout_seconds=timeout_seconds,
            env=env,
            workdir=workdir,
            check=check,
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
        """Runs code inside Monty and returns the execution result."""
        if language != "python":
            raise NotImplementedError(
                "MontySandboxSession.run_code currently only supports "
                "language='python'."
            )

        return self._run_monty_code(
            code=code,
            inputs=inputs,
            timeout_seconds=timeout_seconds,
            env=None,
            workdir=None,
            check=check,
        )

    def code_interpreter(self) -> CodeInterpreter:
        """Creates a persistent code interpreter for repeated execution."""
        interpreter = MontyCodeInterpreter(self)
        self._active_interpreter = interpreter
        return interpreter

    def _store_repl_state(self, state: Optional[bytes]) -> None:
        """Stores serialized repl state produced by interpreter runs."""
        if state is None:
            return

        self._repl_state = state
        self._metadata.extra["snapshot_bytes"] = len(state)

    def snapshot(self) -> Optional[str]:
        """Snapshots interpreter state and returns a serialized payload."""
        if self._active_interpreter is not None:
            self._store_repl_state(self._active_interpreter.dump_state())

        if self._repl_state is None:
            return None

        return base64.b64encode(self._repl_state).decode("ascii")

    def _finalize_metadata(self) -> None:
        """Updates duration metadata based on wall-clock runtime."""
        self._metadata.duration_seconds = max(
            self._metadata.duration_seconds,
            time.monotonic() - self._created_at,
        )

    def terminate(self, reason: Optional[str] = None) -> None:
        """Terminates the active sandbox session."""
        if self._terminated:
            return

        if reason:
            logger.debug("Terminating Monty sandbox session: %s", reason)

        self._terminated = True
        self._finalize_metadata()

    def __enter__(self) -> "SandboxSession":
        """Enters the sandbox session context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exits the sandbox session context manager."""
        self.terminate(reason="session context exited")


class MontySandbox(BaseSandbox):
    """Monty implementation of the ZenML sandbox stack component."""

    @property
    def config(self) -> MontySandboxConfig:
        """Typed Monty sandbox configuration."""
        return cast(MontySandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for step-level sandbox overrides."""
        return MontySandboxSettings

    @property
    def capabilities(self) -> Set[SandboxCapability]:
        """Capabilities supported by the Monty sandbox provider."""
        return {
            SandboxCapability.SNAPSHOTS,
            SandboxCapability.PERSISTENT_SESSIONS,
        }

    def _resolve_step_settings(self) -> MontySandboxSettings:
        """Resolves step-level settings if called from inside a running step."""
        base_settings = MontySandboxSettings.model_validate(
            self.config.model_dump(exclude_unset=True)
        )

        try:
            from zenml.steps import get_step_context

            step_context = get_step_context()
            return cast(
                MontySandboxSettings, self.get_settings(step_context.step_run)
            )
        except RuntimeError:
            return base_settings
        except Exception:
            logger.debug(
                "Failed to resolve Monty sandbox step settings. Falling back "
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
        """Creates a Monty sandbox session and returns its context manager."""
        step_settings = self._resolve_step_settings()

        effective_timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else (
                step_settings.timeout_seconds
                if step_settings.timeout_seconds is not None
                else 300
            )
        )
        effective_memory_mb = (
            memory_mb
            if memory_mb is not None
            else step_settings.memory_mb
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

        effective_network_policy: Optional[NetworkPolicy]
        if network_policy is not None:
            effective_network_policy = network_policy
        else:
            effective_network_policy = step_settings.network_policy

        declared_external_functions = sorted(
            (step_settings.external_functions or {}).keys()
        )

        metadata = SandboxSessionMetadata(
            session_id=f"monty-{uuid4().hex}",
            provider=self.flavor,
            estimated_cost_usd=0.0,
            network_policy=effective_network_policy,
            tags=effective_tags,
            extra={
                "type_check_enabled": self.config.type_check,
                "type_check_stubs_provided": bool(
                    step_settings.type_check_stubs
                ),
                "external_functions_declared": declared_external_functions,
                "external_functions_used": [],
                "execution_backend": "pydantic-monty",
                "env_keys": sorted(effective_env.keys()),
                "requested_image": image or step_settings.image,
                "requested_cpu": cpu
                if cpu is not None
                else step_settings.cpu,
                "requested_memory_mb": effective_memory_mb,
                "requested_gpu": gpu
                if gpu is not None
                else step_settings.gpu,
                "workdir": workdir,
            },
        )
        self._track_session(metadata)

        return MontySandboxSession(
            raise_on_failure=self.config.raise_on_failure,
            metadata=metadata,
            timeout_seconds=effective_timeout_seconds,
            type_check=self.config.type_check,
            type_check_stubs=step_settings.type_check_stubs,
            declared_external_functions=declared_external_functions,
            env=effective_env,
            workdir=workdir,
            memory_mb=effective_memory_mb,
            script_name=_DEFAULT_SCRIPT_NAME,
        )
