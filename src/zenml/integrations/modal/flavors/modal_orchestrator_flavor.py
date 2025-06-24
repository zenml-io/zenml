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
        timeout: Maximum execution time in seconds (default 24h).
        execution_mode: Execution mode - PIPELINE (fastest) or PER_STEP (granular).
        max_parallelism: Maximum number of parallel sandboxes (for PER_STEP mode).
        synchronous: Wait for completion (True) or fire-and-forget (False).
    """

    gpu: Optional[str] = None
    region: Optional[str] = None
    cloud: Optional[str] = None
    modal_environment: Optional[str] = None
    timeout: int = 86400  # 24 hours (Modal's maximum)
    execution_mode: ModalExecutionMode = (
        ModalExecutionMode.PIPELINE
    )  # Default to fastest mode
    max_parallelism: Optional[int] = (
        None  # Maximum number of parallel sandboxes (for PER_STEP mode)
    )
    synchronous: bool = (
        True  # Wait for completion (True) or fire-and-forget (False)
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

    token_id: Optional[str] = SecretField(default=None)
    token_secret: Optional[str] = SecretField(default=None)
    workspace: Optional[str] = None

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
