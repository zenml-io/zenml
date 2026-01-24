#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Run:AI orchestrator flavor."""

from typing import TYPE_CHECKING, Dict, Literal, Optional, Type

from pydantic import (
    Field,
    PositiveFloat,
    PositiveInt,
    SecretStr,
    field_validator,
)

from zenml.config.base_settings import BaseSettings
from zenml.integrations.runai import RUNAI_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.runai.orchestrators import RunAIOrchestrator


class RunAIOrchestratorSettings(BaseSettings):
    """Settings for the Run:AI orchestrator.

    Configuration options for how pipeline steps are executed on Run:AI clusters.
    Provides fractional GPU allocation and compute resource management.
    """

    synchronous: bool = Field(
        default=True,
        description="Controls whether pipeline execution blocks the client. "
        "If True, the client waits until all steps complete. If False, "
        "returns immediately and executes asynchronously",
    )

    # GPU configuration - key feature for Run:AI
    gpu_devices_request: int = Field(
        default=1,
        ge=0,
        description="Number of GPUs to request for the workload. Set to 0 "
        "for CPU-only execution. Examples: 1 for single GPU, 2 for dual GPU, "
        "0 for CPU-only",
    )
    gpu_portion_request: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fractional GPU allocation as a decimal (0.0-1.0). "
        "Enables sharing GPUs across workloads. Examples: 1.0 for full GPU, "
        "0.5 for half GPU, 0.25 for quarter GPU. Only used when gpu_request_type='portion'",
    )
    gpu_request_type: Literal["portion", "device"] = Field(
        default="portion",
        description="GPU allocation method. 'portion' enables fractional GPU sharing "
        "via gpu_portion_request. 'device' allocates whole GPUs via gpu_devices_request",
    )

    # CPU and memory configuration
    cpu_core_request: float = Field(
        default=1.0,
        ge=0.1,
        description="Number of CPU cores to request. Examples: 1.0 for one core, "
        "2.5 for two and a half cores, 0.5 for half a core",
    )
    cpu_memory_request: str = Field(
        default="4G",
        description="Memory to request in Kubernetes format. Valid units: K, M, G, T, Ki, Mi, Gi, Ti. "
        "Examples: '4G' for 4 gigabytes, '512M' for 512 megabytes, '8Gi' for 8 gibibytes",
    )

    # Environment variables
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the Run:AI workload container. "
        "Example: {'LOG_LEVEL': 'DEBUG', 'BATCH_SIZE': '32'}",
    )

    # Workload type (for future inference support)
    workload_type: Literal["training", "inference"] = Field(
        default="training",
        description="Run:AI workload type. 'training' for batch ML training jobs. "
        "'inference' for long-running inference services (experimental)",
    )

    @field_validator("cpu_memory_request")
    @classmethod
    def _validate_memory_format(cls, value: str) -> str:
        """Validates memory request format.

        Args:
            value: The memory request value.

        Returns:
            The validated value.

        Raises:
            ValueError: If the memory format is invalid.
        """
        # Check that the value ends with a valid unit
        valid_units = ["K", "M", "G", "T", "Ki", "Mi", "Gi", "Ti"]
        if not any(value.endswith(unit) for unit in valid_units):
            raise ValueError(
                f"Invalid memory format: {value}. Must end with one of: {valid_units}"
            )

        # Extract the numeric part and validate it
        numeric_part = value.rstrip("KMGTi")
        try:
            float(numeric_part)
        except ValueError as exc:
            raise ValueError(
                f"Invalid memory format: {value}. Numeric part must be a valid number"
            ) from exc

        return value


class RunAIOrchestratorConfig(
    BaseOrchestratorConfig, RunAIOrchestratorSettings
):
    """Configuration for the Run:AI orchestrator.

    Combines base orchestrator configuration with Run:AI-specific settings
    including authentication and project configuration.
    """

    # Run:AI authentication
    client_id: str = Field(
        ...,
        description="Run:AI client ID for API authentication. Obtain from Run:AI "
        "control plane under Settings > Application > Applications. Required for API access",
    )
    client_secret: SecretStr = Field(
        ...,
        description="Run:AI client secret for API authentication. Obtain from Run:AI "
        "control plane under Settings > Application > Applications. Stored securely",
    )
    runai_base_url: str = Field(
        ...,
        description="Run:AI control plane base URL. For SaaS deployments, use format "
        "'https://<organization>.run.ai'. For self-hosted, use your control plane URL. "
        "Example: 'https://my-org.run.ai'",
    )

    # Run:AI project configuration
    project_name: str = Field(
        ...,
        description="Run:AI project name for workload submission. The project must "
        "exist in the Run:AI control plane and have sufficient quota. Workloads are "
        "billed against this project's resources",
    )
    cluster_name: Optional[str] = Field(
        default=None,
        description="Run:AI cluster name for workload execution. If not specified, "
        "the orchestrator will use the first available cluster. For multi-cluster "
        "deployments, specify the target cluster explicitly",
    )

    # Monitoring configuration
    monitoring_interval: PositiveFloat = Field(
        default=30.0,
        description="Interval in seconds to poll Run:AI API for workload status. "
        "Lower values provide faster status updates but increase API load. "
        "Recommended: 30-60 seconds for production",
    )
    workload_timeout: Optional[PositiveInt] = Field(
        default=None,
        description="Maximum time in seconds to wait for workload completion. "
        "If the workload doesn't finish within this time, it will be marked as failed. "
        "If not set, workloads can run indefinitely. Example: 3600 for 1 hour",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Run:AI orchestrator always runs remotely on Run:AI clusters.

        Returns:
            Always True for Run:AI orchestrator.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Run:AI orchestrator never runs locally.

        Returns:
            Always False for Run:AI orchestrator.
        """
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronously.

        Returns:
            True if synchronous execution is configured.
        """
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator supports scheduling.

        Returns:
            True - Run:AI orchestrator supports scheduling.
        """
        return True


class RunAIOrchestratorFlavor(BaseOrchestratorFlavor):
    """Run:AI orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return RUNAI_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        # Using Run:AI official logo
        return "https://www.run.ai/wp-content/uploads/2023/01/runai-logo.svg"

    @property
    def config_class(self) -> Type[RunAIOrchestratorConfig]:
        """Returns RunAIOrchestratorConfig config class.

        Returns:
            The config class.
        """
        return RunAIOrchestratorConfig

    @property
    def implementation_class(self) -> Type["RunAIOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.runai.orchestrators import RunAIOrchestrator

        return RunAIOrchestrator
