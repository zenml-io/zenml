#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Base abstractions for ZenML sandbox stack components."""

from abc import ABC, abstractmethod
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

from pydantic import BaseModel, Field

from zenml.config.base_settings import BaseSettings
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponent, StackComponentConfig
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)

JsonSerializable = Union[
    str, int, float, bool, None, Dict[str, Any], List[Any]
]


class SandboxCapability(StrEnum):
    """Capabilities that sandbox providers may expose."""

    FILESYSTEM = "filesystem"
    NETWORKING = "networking"
    TUNNELS = "tunnels"
    SNAPSHOTS = "snapshots"
    STREAMING_OUTPUT = "streaming"
    PERSISTENT_SESSIONS = "persistent"
    GPU = "gpu"
    EXEC_CANCEL = "exec_cancel"


class NetworkPolicy(BaseModel):
    """Structured network policy for sandbox sessions."""

    block_network: bool = False
    cidr_allowlist: Optional[List[str]] = None


class SandboxSessionMetadata(BaseModel):
    """Metadata for a single sandbox session within a step run."""

    session_id: str
    provider: str
    sandbox_url: Optional[str] = None
    duration_seconds: float = 0.0
    commands_executed: int = 0
    estimated_cost_usd: Optional[float] = None
    network_policy: Optional[NetworkPolicy] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)


class SandboxRunMetadata(BaseModel):
    """Public metadata model emitted for sandbox-enabled steps."""

    provider: str
    session_count: int = 0
    sessions: List[SandboxSessionMetadata] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_commands_executed: int = 0
    total_estimated_cost_usd: Optional[float] = None
    capabilities: List[str] = Field(default_factory=list)


class SandboxExecResult(BaseModel):
    """Result of command or code execution in a sandbox session."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    output: Optional[JsonSerializable] = None


class SandboxExecError(Exception):
    """Raised when a sandbox execution exits with a non-zero status."""

    def __init__(self, result: SandboxExecResult):
        """Initializes the error with the execution result.

        Args:
            result: The full execution result.
        """
        self.result = result
        stderr_tail = (
            "\n".join(result.stderr.splitlines()[-10:])
            if result.stderr
            else ""
        )
        super().__init__(
            f"Sandbox command failed with exit code {result.exit_code}"
            f"{': ' + stderr_tail if stderr_tail else ''}"
        )


class SandboxProcess(ABC):
    """Handle to a running process inside a sandbox session."""

    @abstractmethod
    def stdout_iter(self) -> Iterator[str]:
        """Iterates over stdout chunks as they are produced."""

    @abstractmethod
    def stderr_iter(self) -> Iterator[str]:
        """Iterates over stderr chunks as they are produced."""

    @abstractmethod
    def wait(self, timeout_seconds: Optional[int] = None) -> int:
        """Waits for process completion and returns the exit code."""

    @property
    @abstractmethod
    def exit_code(self) -> Optional[int]:
        """Returns the process exit code when available."""

    def kill(self) -> None:
        """Terminates this process.

        Providers without process-level cancellation can override this by
        terminating the full session instead.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support killing individual "
            "processes. Use session.terminate() instead."
        )


class CodeInterpreter(ABC):
    """Persistent code execution interface running inside a session."""

    @abstractmethod
    def run(
        self,
        code: str,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> SandboxExecResult:
        """Executes code while preserving interpreter state between calls."""

    @abstractmethod
    def __enter__(self) -> "CodeInterpreter":
        """Starts the interpreter session."""

    @abstractmethod
    def __exit__(self, *args: Any) -> None:
        """Stops the interpreter session."""


class SandboxSession(ABC):
    """Base interface for an active sandbox session."""

    @abstractmethod
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

    @abstractmethod
    def run_code(
        self,
        code: str,
        *,
        language: str = "python",
        inputs: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        check: Optional[bool] = None,
    ) -> SandboxExecResult:
        """Runs a code snippet and returns the execution result."""

    @abstractmethod
    def terminate(self, reason: Optional[str] = None) -> None:
        """Terminates the active sandbox session."""

    @abstractmethod
    def __enter__(self) -> "SandboxSession":
        """Enters the sandbox session context manager."""

    @abstractmethod
    def __exit__(self, *args: Any) -> None:
        """Exits the sandbox session context manager."""

    def exec_streaming(
        self,
        command: List[str],
        *,
        timeout_seconds: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> SandboxProcess:
        """Runs a command and yields streaming process output."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support streaming output."
        )

    def code_interpreter(self) -> CodeInterpreter:
        """Creates a persistent interpreter for repeated code execution."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support code interpreter mode."
        )

    def write_file(self, remote_path: str, content: Union[bytes, str]) -> None:
        """Writes content to a path in the sandbox filesystem."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support filesystem operations."
        )

    def read_file(self, remote_path: str) -> bytes:
        """Reads file content from the sandbox filesystem."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support filesystem operations."
        )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Uploads a local file into the sandbox filesystem."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support filesystem operations."
        )

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Downloads a file from the sandbox filesystem to local storage."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support filesystem operations."
        )

    def snapshot(self) -> Optional[str]:
        """Snapshots sandbox state and returns a provider-specific ID."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support snapshots."
        )

    def open_tunnel(self, port: int) -> Optional[str]:
        """Opens a tunnel to a sandbox port and returns a reachable URL."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support tunnels."
        )


class BaseSandboxConfig(StackComponentConfig):
    """Base configuration for sandbox stack components."""

    raise_on_failure: bool = True

    @property
    def is_remote(self) -> bool:
        """Whether this sandbox component requires remote stack execution."""
        return True

    @property
    def is_local(self) -> bool:
        """Whether this sandbox component is local-only."""
        return not self.is_remote


class BaseSandboxSettings(BaseSettings):
    """Step-level sandbox settings that override component defaults."""

    timeout_seconds: Optional[int] = None
    image: Optional[str] = None
    cpu: Optional[float] = None
    memory_mb: Optional[int] = None
    gpu: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    secret_refs: Optional[List[str]] = None
    network_policy: Optional[NetworkPolicy] = None
    tags: Optional[Dict[str, str]] = None


class BaseSandbox(StackComponent, ABC):
    """Base class for all ZenML sandbox components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes internal tracking used for metadata emission."""
        super().__init__(*args, **kwargs)
        self._step_sessions: List[SandboxSessionMetadata] = []

    @property
    def config(self) -> BaseSandboxConfig:
        """Typed sandbox component configuration."""
        return cast(BaseSandboxConfig, self._config)

    @property
    def capabilities(self) -> Set[SandboxCapability]:
        """Capabilities supported by this sandbox provider."""
        return set()

    def has_capability(self, cap: SandboxCapability) -> bool:
        """Checks whether the provider supports a specific capability.

        Args:
            cap: The capability to check.

        Returns:
            Whether the capability is supported.
        """
        return cap in self.capabilities

    @abstractmethod
    def session(
        self,
        *,
        image: Optional[str] = None,
        cpu: Optional[float] = None,
        memory_mb: Optional[int] = None,
        gpu: Optional[str] = None,
        timeout_seconds: int = 300,
        env: Optional[Dict[str, str]] = None,
        secret_refs: Optional[List[str]] = None,
        network_policy: Optional[NetworkPolicy] = None,
        tags: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> SandboxSession:
        """Creates a sandbox session and returns its context manager."""

    def _track_session(self, metadata: SandboxSessionMetadata) -> None:
        """Tracks a session for step-level metadata emission.

        Args:
            metadata: Metadata for the session that was created.
        """
        self._step_sessions.append(metadata)

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Resets step-level tracking for a new step run.

        Args:
            info: Info about the step that will be executed.
        """
        self._step_sessions = []

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Emits warnings about unusual sandbox usage patterns.

        Args:
            info: Info about the executed step.
            step_failed: Whether the step failed.
        """
        if not getattr(info.config, "sandbox", False):
            return

        if self._step_sessions:
            return

        step_name = getattr(info.config, "name", "unknown")
        logger.warning(
            "Step '%s' declared sandbox=True but no sandbox sessions were "
            "created. Did you forget to call sandbox.session()?",
            step_name,
        )

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Returns structured sandbox metadata for the step run.

        Args:
            info: Info about the executed step.

        Returns:
            Serialized sandbox metadata keyed by `sandbox_info`.
        """
        if not self._step_sessions:
            return {}

        estimated_costs = [
            session.estimated_cost_usd
            for session in self._step_sessions
            if session.estimated_cost_usd is not None
        ]
        metadata = SandboxRunMetadata(
            provider=self.flavor,
            session_count=len(self._step_sessions),
            sessions=self._step_sessions,
            total_duration_seconds=sum(
                session.duration_seconds for session in self._step_sessions
            ),
            total_commands_executed=sum(
                session.commands_executed for session in self._step_sessions
            ),
            total_estimated_cost_usd=sum(estimated_costs)
            if estimated_costs
            else None,
            capabilities=sorted(
                capability.value for capability in self.capabilities
            ),
        )
        return {"sandbox_info": metadata.model_dump_json()}


class BaseSandboxFlavor(Flavor):
    """Base flavor contract for sandbox implementations."""

    @property
    def type(self) -> StackComponentType:
        """Returns the stack component type for sandbox flavors."""
        return StackComponentType.SANDBOX

    @property
    @abstractmethod
    def config_class(self) -> Type[BaseSandboxConfig]:
        """Returns the configuration class for this sandbox flavor."""

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseSandbox]:
        """Returns the stack component class for this sandbox flavor."""
