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
"""Run:AI deployer flavor."""

from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Type

from pydantic import (
    Field,
    PositiveFloat,
    SecretStr,
    field_validator,
    model_validator,
)

from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.integrations.runai import RUNAI_DEPLOYER_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.runai.deployers import RunAIDeployer


class RunAIDeployerSettings(BaseDeployerSettings):
    """Per-deployment settings for Run:AI inference workloads.

    These settings can be configured when deploying a pipeline snapshot:

    ```python
    snapshot = client.create_pipeline_snapshot(
        pipeline="my_pipeline",
        deployer_settings={"gpu_portion_request": 0.5}
    )
    ```
    """

    gpu_devices_request: int = Field(
        default=1,
        ge=0,
        description="Number of GPUs to request for the inference workload. "
        "Default 1 requests a whole device; set to 0 for CPU-only or keep 1 with "
        "gpu_portion_request < 1.0 to request a fractional share",
    )
    gpu_portion_request: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fractional GPU allocation as a decimal (0.0-1.0). "
        "Default 1.0 requests a full device; lower values (e.g., 0.5 or 0.25) "
        "share a GPU across workloads. Used when gpu_request_type='portion'",
    )
    gpu_request_type: Literal["portion", "memory"] = Field(
        default="portion",
        description="GPU allocation method. 'portion' for fractional GPU sharing, "
        "'memory' for exact memory allocation",
    )
    gpu_memory_request: Optional[str] = Field(
        default=None,
        description="GPU memory to request (e.g., '20Gi'). Used when "
        "gpu_request_type='memory'",
    )

    cpu_core_request: float = Field(
        default=1.0,
        ge=0.1,
        description="Number of CPU cores to request. Examples: 1.0 for one core, "
        "2.5 for two and a half cores",
    )
    cpu_memory_request: str = Field(
        default="4G",
        description="RAM to request for the inference container. Must use Kubernetes "
        "format with valid units: K, M, G, T, Ki, Mi, Gi, Ti. Examples: '4G', '8Gi'",
    )

    min_replicas: int = Field(
        default=1,
        ge=0,
        description="Minimum number of replicas for the inference workload. "
        "Set to 0 to allow scale-to-zero behavior",
    )
    max_replicas: int = Field(
        default=3,
        ge=1,
        description="Maximum number of replicas for autoscaling the inference workload",
    )

    autoscaling_metric: Optional[
        Literal["concurrency", "throughput", "latency"]
    ] = Field(
        default="concurrency",
        description="Metric for autoscaling decisions when min_replicas < max_replicas. "
        "'concurrency' scales based on concurrent requests per replica, "
        "'throughput' scales based on requests per second, "
        "'latency' scales based on response latency",
    )
    autoscaling_metric_threshold: int = Field(
        default=10,
        ge=1,
        description="Threshold value for the autoscaling metric. For 'concurrency', "
        "this is the target concurrent requests per replica. For 'throughput', "
        "this is target requests per second",
    )

    node_pools: Optional[List[str]] = Field(
        default=None,
        description="Ordered list of node pool names for scheduling",
    )
    node_type: Optional[str] = Field(
        default=None,
        description="Node type label for GPU selection (e.g., 'A100', 'V100')",
    )

    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Kubernetes labels to add to the inference workload pod",
    )
    annotations: Dict[str, str] = Field(
        default_factory=dict,
        description="Kubernetes annotations to add to the inference workload pod",
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables to set in the inference container",
    )

    workload_name_prefix: str = Field(
        default="zenml-",
        description="Prefix for inference workload names to avoid naming conflicts",
    )

    @field_validator(
        "cpu_memory_request",
        "gpu_memory_request",
    )
    @classmethod
    def _validate_memory_format(cls, value: Optional[str]) -> Optional[str]:
        """Validates memory request format.

        Args:
            value: The memory value.

        Returns:
            The validated value.

        Raises:
            ValueError: If the memory format is invalid.
        """
        if value is None:
            return None

        valid_units = ["K", "M", "G", "T", "Ki", "Mi", "Gi", "Ti"]
        if not any(value.endswith(unit) for unit in valid_units):
            raise ValueError(
                f"Invalid memory format: {value}. Must end with one of: {valid_units}"
            )

        numeric_part = value.rstrip("KMGTi")
        try:
            float(numeric_part)
        except ValueError as exc:
            raise ValueError(
                f"Invalid memory format: {value}. Numeric part must be a valid number"
            ) from exc

        return value

    @model_validator(mode="after")
    def _validate_gpu_settings(self) -> "RunAIDeployerSettings":
        """Validate GPU settings consistency.

        Returns:
            The validated settings.

        Raises:
            ValueError: If GPU settings are inconsistent.
        """
        if self.gpu_request_type == "memory" and not self.gpu_memory_request:
            raise ValueError(
                "gpu_memory_request is required when gpu_request_type='memory'"
            )
        return self

    @model_validator(mode="after")
    def _validate_replica_settings(self) -> "RunAIDeployerSettings":
        """Validate replica settings consistency.

        Returns:
            The validated settings.

        Raises:
            ValueError: If replica settings are inconsistent.
        """
        if self.max_replicas < self.min_replicas:
            raise ValueError(
                f"max_replicas ({self.max_replicas}) must be >= "
                f"min_replicas ({self.min_replicas})"
            )
        return self


class RunAIDeployerConfig(BaseDeployerConfig, RunAIDeployerSettings):
    """Configuration for the Run:AI deployer.

    This deployer enables deploying inference workloads on Run:AI clusters
    with fractional GPU allocation and autoscaling.

    Example stack configuration:
    ```bash
    zenml deployer register runai \\
        --flavor=runai \\
        --client_id="xxx" \\
        --client_secret="xxx" \\
        --runai_base_url="https://myorg.run.ai" \\
        --project_name="my-project"
    ```
    """

    client_id: str = Field(
        ...,
        description="Run:AI client ID for API authentication. Obtain from Run:AI "
        "control plane under Settings > Application > Applications",
    )
    client_secret: SecretStr = Field(
        ...,
        description="Run:AI client secret for API authentication. Obtain from Run:AI "
        "control plane under Settings > Application > Applications",
    )
    runai_base_url: str = Field(
        ...,
        description="Run:AI control plane base URL. For SaaS deployments, use format "
        "'https://<organization>.run.ai'. Example: 'https://my-org.run.ai'",
    )

    project_name: str = Field(
        ...,
        description="Run:AI project name for workload submission. The project must "
        "exist in the Run:AI control plane and have sufficient quota",
    )
    cluster_name: Optional[str] = Field(
        default=None,
        description="Run:AI cluster name for workload execution. If not specified, "
        "uses the cluster associated with the project or the first available cluster",
    )

    image_pull_secret_name: Optional[str] = Field(
        default=None,
        description="Name of an existing Run:AI image pull secret for private registries. "
        "Create the secret in Run:AI UI under Credentials > Docker Registry",
    )

    monitoring_interval: PositiveFloat = Field(
        default=30.0,
        description="Interval in seconds to poll Run:AI API for workload status",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Run:AI deployer always runs remotely on Run:AI clusters.

        Returns:
            Always True for Run:AI deployer.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Run:AI deployer never runs locally.

        Returns:
            Always False for Run:AI deployer.
        """
        return False


class RunAIDeployerFlavor(BaseDeployerFlavor):
    """Run:AI deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return RUNAI_DEPLOYER_FLAVOR

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
        return "https://www.run.ai/wp-content/uploads/2023/01/runai-logo.svg"

    @property
    def config_class(self) -> Type[RunAIDeployerConfig]:
        """Returns RunAIDeployerConfig config class.

        Returns:
            The config class.
        """
        return RunAIDeployerConfig

    @property
    def implementation_class(self) -> Type["RunAIDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.runai.deployers import RunAIDeployer

        return RunAIDeployer
