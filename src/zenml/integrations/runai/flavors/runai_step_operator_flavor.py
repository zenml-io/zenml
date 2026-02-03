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
"""Run:AI step operator flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Type

from pydantic import (
    Field,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from zenml.config.base_settings import BaseSettings
from zenml.integrations.runai import RUNAI_STEP_OPERATOR_FLAVOR
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor
from zenml.utils.secret_utils import PlainSerializedSecretStr

if TYPE_CHECKING:
    from zenml.integrations.runai.step_operators import RunAIStepOperator


class RunAIStepOperatorSettings(BaseSettings):
    """Per-step settings for Run:AI execution.

    These settings can be configured per-step using the step decorator:

    ```python
    @step(
        step_operator="runai",
        settings={"step_operator": {"gpu_portion_request": 0.5}}
    )
    def my_step():
        ...
    ```
    """

    gpu_devices_request: int = Field(
        default=1,
        ge=0,
        description="Number of GPUs to request for the workload. Default 1 "
        "requests a whole device; set to 0 for CPU-only or keep 1 with "
        "gpu_portion_request < 1.0 to request a fractional share. Examples: "
        "1 for single GPU, 2 for dual GPU, 0 for CPU-only. Pair with "
        "gpu_request_type='portion' to control fractional allocation.",
    )
    gpu_portion_request: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fractional GPU allocation as a decimal (0.0-1.0). "
        "Default 1.0 requests a full device; lower values (e.g., 0.5 or 0.25) "
        "share a GPU across workloads. Used when gpu_request_type='portion'.",
    )
    gpu_request_type: Literal["portion", "memory"] = Field(
        default="portion",
        description="GPU allocation method. 'portion' for fractional GPU sharing "
        "(use gpu_portion_request: 1.0 for full GPU, 0.5 for half). "
        "'memory' for exact memory allocation (gpu_memory_request)",
    )
    gpu_memory_request: Optional[str] = Field(
        default=None,
        description="GPU memory to request (e.g., '20Gi'). Used when "
        "gpu_request_type='memory'. Provides consistent memory allocation "
        "across heterogeneous GPU types",
    )

    gpu_portion_limit: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum GPU portion limit for dynamic fractions. Enables burst: "
        "workload gets gpu_portion_request guaranteed, can use up to this limit when available",
    )
    gpu_memory_limit: Optional[str] = Field(
        default=None,
        description="Maximum GPU memory limit for dynamic fractions (e.g., '40Gi'). "
        "Used with gpu_memory_request for burst capacity",
    )

    cpu_core_request: float = Field(
        default=1.0,
        ge=0.1,
        description="Number of CPU cores to request. Examples: 1.0 for one core, "
        "2.5 for two and a half cores, 0.5 for half a core",
    )
    cpu_core_limit: Optional[float] = Field(
        default=None,
        ge=0.1,
        description="Maximum CPU cores limit. If set, allows bursting from "
        "cpu_core_request to this limit",
    )
    cpu_memory_request: str = Field(
        default="4G",
        description="RAM to request for the workload container. Must use Kubernetes "
        "format with valid units: K, M, G, T, Ki, Mi, Gi, Ti. Examples: '4G' "
        "for 4 gigabytes, '512M' for 512 megabytes, '8Gi' for 8 gibibytes. "
        "Default is sufficient for most training jobs.",
    )
    cpu_memory_limit: Optional[str] = Field(
        default=None,
        description="Maximum memory limit (e.g., '16Gi'). If set, allows bursting "
        "from cpu_memory_request",
    )

    node_pools: Optional[List[str]] = Field(
        default=None,
        description="Ordered list of node pool names for scheduling. Scheduler tries pools "
        "in order. Node pools group nodes by GPU type, InfiniBand, etc. "
        "Example: ['a100-pool', 'v100-pool']",
    )
    node_type: Optional[str] = Field(
        default=None,
        description="Node type label for GPU selection (e.g., 'A100', 'V100'). "
        "Alternative to node_pools for simpler GPU type selection",
    )

    preemptibility: Optional[Literal["preemptible", "non-preemptible"]] = (
        Field(
            default=None,
            description="Workload preemption policy. 'preemptible' allows over-quota usage "
            "but may be preempted by higher priority workloads. 'non-preemptible' guarantees "
            "resources within quota",
        )
    )
    priority_class: Optional[str] = Field(
        default=None,
        description="Kubernetes PriorityClass name for scheduling priority within project queue. "
        "Run:AI presets: 'train' (50), 'build' (50), 'interactive-preemptible' (100), 'inference' (125)",
    )

    tolerations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Kubernetes tolerations for scheduling on tainted nodes. Each item: "
        "{'key': str, 'operator': 'Equal'|'Exists', 'value': str, "
        "'effect': 'NoSchedule'|'PreferNoSchedule'|'NoExecute'}. "
        "Example: [{'key': 'nvidia.com/gpu', 'operator': 'Exists', 'effect': 'NoSchedule'}]",
    )

    extended_resources: Optional[Dict[str, str]] = Field(
        default=None,
        description="Extended Kubernetes resources (InfiniBand, FPGAs, etc). "
        "Format: {resource_name: quantity}. Example: {'nvidia.com/mlnx-nic': '1', 'rdma/hca': '1'}",
    )
    large_shm_request: bool = Field(
        default=False,
        description="Request large /dev/shm (shared memory). Required for PyTorch DataLoader "
        "with num_workers > 0, or multi-process training that uses shared memory",
    )

    backoff_limit: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of retries before marking workload as failed. Default is 6 in "
        "Kubernetes. Set to 0 for no retries",
    )
    termination_grace_period_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Seconds to wait for graceful termination before force killing. "
        "Default is 30 seconds. Increase for workloads needing cleanup time",
    )
    terminate_after_preemption: Optional[bool] = Field(
        default=None,
        description="If True, terminate workload after preemption instead of requeuing. "
        "Default is False (workload gets rescheduled)",
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Working directory inside container. If not set, uses container's default",
    )

    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Kubernetes labels to add to the workload pod. "
        "Example: {'team': 'ml-research', 'cost-center': 'ai-division'}",
    )
    annotations: Optional[Dict[str, str]] = Field(
        default=None,
        description="Kubernetes annotations to add to the workload pod. "
        "Example: {'prometheus.io/scrape': 'true'}",
    )

    workload_timeout: Optional[PositiveInt] = Field(
        default=None,
        description="Maximum time in seconds to wait for workload completion. "
        "If the workload doesn't finish within this time, it will be marked as failed. "
        "If not set, workloads can run indefinitely. Example: 3600 for 1 hour",
    )
    pending_timeout: Optional[PositiveInt] = Field(
        default=None,
        description="Maximum time in seconds a workload may remain in the pending state "
        "before it is stopped. If not set, workloads can remain pending indefinitely. "
        "Example: 600 for 10 minutes",
    )

    @field_validator(
        "cpu_memory_request",
        "cpu_memory_limit",
        "gpu_memory_request",
        "gpu_memory_limit",
    )
    @classmethod
    def _validate_memory_format(cls, value: Optional[str]) -> Optional[str]:
        """Validates memory request/limit format.

        Args:
            value: The memory value.

        Returns:
            The validated value.

        Raises:
            ValueError: If the memory format is invalid.
        """
        if value is None:
            return None

        import re

        # Use regex for stricter validation
        pattern = r"^(\d+(?:\.\d+)?)(K|M|G|T|Ki|Mi|Gi|Ti)$"
        if not re.match(pattern, value):
            raise ValueError(
                f"Invalid memory format: {value}. "
                f"Must be a number followed by one of: K, M, G, T, Ki, Mi, Gi, Ti. "
                f"Examples: '4G', '512M', '8Gi'"
            )

        return value

    @model_validator(mode="after")
    def _validate_gpu_settings(self) -> "RunAIStepOperatorSettings":
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
        if self.gpu_portion_limit is not None:
            if self.gpu_portion_limit < self.gpu_portion_request:
                raise ValueError(
                    "gpu_portion_limit must be >= gpu_portion_request"
                )
        return self


class RunAIStepOperatorConfig(
    BaseStepOperatorConfig, RunAIStepOperatorSettings
):
    """Configuration for the Run:AI step operator.

    This step operator enables running individual pipeline steps on Run:AI
    clusters with fractional GPU allocation.

    Example stack configuration:
    ```bash
    zenml step-operator register runai \\
        --flavor=runai \\
        --client_id="xxx" \\
        --client_secret="xxx" \\
        --runai_base_url="https://myorg.run.ai" \\
        --project_name="my-project"
    ```
    """

    client_id: PlainSerializedSecretStr = Field(
        ...,
        description="Run:AI client ID for API authentication. Obtain from Run:AI "
        "control plane under Settings > Application > Applications. Required for API access",
    )
    client_secret: PlainSerializedSecretStr = Field(
        ...,
        description="Run:AI client secret for API authentication. Obtain from Run:AI "
        "control plane under Settings > Application > Applications.",
    )
    runai_base_url: str = Field(
        ...,
        description="Run:AI control plane base URL. For Run:AI SaaS, use format "
        "'https://<organization>.run.ai'. For self-hosted Run:AI deployments, use your control plane URL. "
        "Example: 'https://my-org.run.ai'",
    )

    @field_validator("runai_base_url")
    @classmethod
    def _validate_runai_base_url(cls, value: str) -> str:
        """Validate and normalize Run:AI base URL.

        Args:
            value: The URL to validate.

        Returns:
            The validated and normalized URL.

        Raises:
            ValueError: If the URL is invalid.
        """
        if not value.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid URL '{value}'. Must start with http:// or https://"
            )
        return value.rstrip("/")

    project_name: str = Field(
        ...,
        description="Run:AI project name for workload submission. The project must "
        "exist in the Run:AI control plane and have sufficient quota. Workloads are "
        "billed against this project's resources",
    )
    cluster_name: Optional[str] = Field(
        default=None,
        description="Run:AI cluster name for workload execution. If not specified, "
        "uses the cluster associated with the project or the first available cluster",
    )

    image_pull_secret_name: Optional[str] = Field(
        default=None,
        description="Name of an existing Run:AI image pull secret for private registries. "
        "Create the secret in Run:AI UI under Credentials > Docker Registry. "
        "If not specified, assumes the container registry is public or credentials "
        "are pre-configured in the Run:AI project",
    )

    monitoring_interval: PositiveFloat = Field(
        default=30.0,
        description="Interval in seconds to poll Run:AI API for workload status. "
        "Lower values provide faster status updates but increase API load. "
        "Recommended: 30-60 seconds for production",
    )
    delete_on_failure: bool = Field(
        default=False,
        description="Whether to delete Run:AI workloads after they fail or timeout. "
        "Workloads are always stopped on failure to halt resource usage; "
        "set this to True to delete them afterward. Defaults to False to preserve "
        "failed workloads for traceability in the Run:AI UI.",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Run:AI step operator always runs remotely on Run:AI clusters.

        Returns:
            True, as Run:AI step operator always runs remotely.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Run:AI step operator never runs locally.

        Returns:
            False, as Run:AI step operator never runs locally.
        """
        return False


class RunAIStepOperatorFlavor(BaseStepOperatorFlavor):
    """Run:AI step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return RUNAI_STEP_OPERATOR_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "Run:AI"

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
    def config_class(self) -> Type[RunAIStepOperatorConfig]:
        """Returns RunAIStepOperatorConfig config class.

        Returns:
            The config class.
        """
        return RunAIStepOperatorConfig

    @property
    def implementation_class(self) -> Type["RunAIStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.runai.step_operators import RunAIStepOperator

        return RunAIStepOperator
