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
"""Modal orchestrator flavor."""

from enum import Enum
from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.modal.orchestrators import ModalOrchestrator

from zenml.integrations.modal import MODAL_ORCHESTRATOR_FLAVOR


class ModalExecutionMode(str, Enum):
    """Execution modes for the Modal orchestrator.

    Attributes:
        PIPELINE: Execute entire pipeline in one Modal sandbox (fastest, default).
        PER_STEP: Execute each step in a separate Modal sandbox (granular control,
            better for debugging, allows step-specific resources).
    """

    PIPELINE = "pipeline"
    PER_STEP = "per_step"


class ModalOrchestratorSettings(BaseSettings):
    """Modal orchestrator settings.

    Attributes:
        gpu: The type of GPU to use for the pipeline execution (e.g., "T4",
            "A100"). Use ResourceSettings.gpu_count to specify the number of GPUs.
        region: The region to use for the pipeline execution.
        cloud: The cloud provider to use for the pipeline execution.
        modal_environment: The Modal environment to use for the pipeline execution.
        app_name: Custom name for the Modal app (defaults to pipeline name).
        timeout: Maximum execution time in seconds (default 24h).
        mode: Execution mode controlling sandbox allocation. PIPELINE mode runs the
            entire pipeline in a single Modal sandbox (fastest, shared resources).
            PER_STEP mode runs each step in its own sandbox (granular control,
            step-specific resources, better for debugging and resource isolation).
        max_parallelism: Maximum number of parallel sandboxes (for PER_STEP mode).
        synchronous: Wait for completion (True) or fire-and-forget (False).
    """

    gpu: Optional[str] = Field(
        None,
        description="GPU type for pipeline execution. Must be a valid Modal GPU type. "
        "Examples: 'T4' (cost-effective), 'A100' (high-performance), 'V100' (training workloads). "
        "Use ResourceSettings.gpu_count to specify number of GPUs. If not specified, uses CPU-only execution",
    )
    region: Optional[str] = Field(
        None,
        description="Cloud region for pipeline execution. Must be a valid region for the selected cloud provider. "
        "Examples: 'us-east-1', 'us-west-2', 'eu-west-1'. If not specified, Modal uses default region "
        "based on cloud provider and availability",
    )
    cloud: Optional[str] = Field(
        None,
        description="Cloud provider for pipeline execution. Must be a valid Modal-supported cloud provider. "
        "Examples: 'aws', 'gcp'. If not specified, Modal uses default cloud provider "
        "based on workspace configuration",
    )
    modal_environment: Optional[str] = Field(
        None,
        description="Modal environment name for pipeline execution. Must be a valid environment "
        "configured in your Modal workspace. Examples: 'main', 'staging', 'production'. "
        "If not specified, uses the default environment for the workspace",
    )
    app_name: Optional[str] = Field(
        None,
        description="Specifies custom name for the Modal app used for pipeline execution. "
        "Must be a valid Modal app name containing only alphanumeric characters, "
        "hyphens, and underscores. Examples: 'ml-training-app', 'data_pipeline_prod', "
        "'zenml-experiments'. If not provided, defaults to 'zenml-pipeline-{pipeline_name}'",
    )
    timeout: int = Field(
        86400,
        description="Maximum execution time in seconds for pipeline completion. Must be between 1 and 86400 seconds. "
        "Examples: 3600 (1 hour), 7200 (2 hours), 86400 (24 hours maximum). "
        "Pipeline execution will be terminated if it exceeds this timeout",
    )
    mode: ModalExecutionMode = Field(
        ModalExecutionMode.PIPELINE,
        description="Execution mode controlling sandbox allocation strategy. PIPELINE mode runs entire pipeline "
        "in single Modal sandbox for fastest execution with shared resources. PER_STEP mode runs each step "
        "in separate sandbox for granular control and resource isolation. Examples: 'pipeline', 'per_step'",
    )
    max_parallelism: Optional[int] = Field(
        None,
        description="Maximum number of parallel sandboxes for PER_STEP execution mode. Must be positive integer. "
        "Examples: 5 (up to 5 parallel steps), 10 (higher parallelism). Only applies when mode='per_step'. "
        "If not specified, Modal determines optimal parallelism based on pipeline structure",
    )
    synchronous: bool = Field(
        True,
        description="Controls whether pipeline execution blocks the client until completion. If True, "
        "client waits for all steps to finish before returning. If False, returns immediately "
        "and executes asynchronously. Useful for long-running production pipelines",
    )


class ModalOrchestratorConfig(
    BaseOrchestratorConfig, ModalOrchestratorSettings
):
    """Modal orchestrator config.

    Attributes:
        token_id: Modal API token ID (ak-xxxxx format) for authentication.
        token_secret: Modal API token secret (as-xxxxx format) for authentication.
        workspace: Modal workspace name (optional).

    Note: If token_id and token_secret are not provided, falls back to
    Modal's default authentication (~/.modal.toml).
    All other configuration options (modal_environment, gpu, region, etc.)
    are inherited from ModalOrchestratorSettings.
    """

    token_id: Optional[str] = SecretField(
        default=None,
        description="Modal API token ID for authentication. Must be in format 'ak-xxxxx' as provided by Modal. "
        "Example: 'ak-1234567890abcdef'. If not provided, falls back to Modal's default authentication "
        "from ~/.modal.toml file. Required for programmatic access to Modal API",
    )
    token_secret: Optional[str] = SecretField(
        default=None,
        description="Modal API token secret for authentication. Must be in format 'as-xxxxx' as provided by Modal. "
        "Example: 'as-abcdef1234567890'. Used together with token_id for API authentication. "
        "If not provided, falls back to Modal's default authentication from ~/.modal.toml file",
    )
    workspace: Optional[str] = Field(
        None,
        description="Modal workspace name for pipeline execution. Must be a valid workspace name "
        "you have access to. Examples: 'my-company', 'ml-team', 'personal-workspace'. "
        "If not specified, uses the default workspace from Modal configuration",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True since Modal runs remotely.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous


class ModalOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Modal orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return MODAL_ORCHESTRATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/modal.png"

    @property
    def config_class(self) -> Type[ModalOrchestratorConfig]:
        """Config class for the Modal orchestrator flavor.

        Returns:
            The config class.
        """
        return ModalOrchestratorConfig

    @property
    def implementation_class(self) -> Type["ModalOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.modal.orchestrators import ModalOrchestrator

        return ModalOrchestrator
