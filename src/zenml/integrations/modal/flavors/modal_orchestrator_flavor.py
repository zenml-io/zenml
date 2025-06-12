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

from typing import TYPE_CHECKING, Optional, Type

from pydantic import SecretStr

from zenml.config.base_settings import BaseSettings
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.modal.orchestrators import ModalOrchestrator

MODAL_ORCHESTRATOR_FLAVOR = "modal"


class ModalOrchestratorSettings(BaseSettings):
    """Modal orchestrator settings.

    Attributes:
        gpu: The type of GPU to use for the pipeline execution.
        region: The region to use for the pipeline execution.
        cloud: The cloud provider to use for the pipeline execution.
        environment: The Modal environment to use for the pipeline execution.
        cpu_count: Number of CPU cores to allocate.
        memory_mb: Memory in MB to allocate.
        timeout: Maximum execution time in seconds (default 24h).
        min_containers: Minimum containers to keep warm (replaces keep_warm).
        max_containers: Maximum concurrent containers (replaces concurrency_limit).
        execution_mode: Execution mode - "pipeline" (default, fastest) or "per_step" (granular control).
        synchronous: Wait for completion (True) or fire-and-forget (False).
    """

    gpu: Optional[str] = None
    region: Optional[str] = None
    cloud: Optional[str] = None
    environment: Optional[str] = None
    cpu_count: Optional[int] = (
        32  # Default 32 CPU cores for blazing fast execution
    )
    memory_mb: Optional[int] = 65536  # Default 64GB RAM for maximum speed
    timeout: int = 86400  # 24 hours (Modal's maximum)
    min_containers: Optional[int] = (
        1  # Keep 1 container warm for sequential execution
    )
    max_containers: Optional[int] = 10  # Allow up to 10 concurrent containers
    execution_mode: str = "pipeline"  # Default to fastest mode
    synchronous: bool = (
        True  # Wait for completion (True) or fire-and-forget (False)
    )


class ModalOrchestratorConfig(
    BaseOrchestratorConfig, ModalOrchestratorSettings
):
    """Modal orchestrator config optimized for BLAZING FAST execution.

    Attributes:
        token: Modal API token for authentication. If not provided,
            falls back to Modal's default authentication (~/.modal.toml).
        workspace: Modal workspace name (optional).
        environment: Modal environment name (optional).
    """

    token: Optional[SecretStr] = None
    workspace: Optional[str] = None
    environment: Optional[str] = None

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
            True since the orchestrator waits for completion.
        """
        return True


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
