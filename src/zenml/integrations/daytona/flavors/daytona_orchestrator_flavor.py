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
"""Daytona orchestrator flavor."""

from typing import TYPE_CHECKING, Dict, List, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.daytona import DAYTONA_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.daytona.orchestrators.daytona_orchestrator import (
        DaytonaOrchestrator,
    )


class DaytonaOrchestratorSettings(BaseSettings):
    """Settings for the Daytona orchestrator.

    Attributes:
        api_key: The API key for authenticating with Daytona.
        server_url: The URL of the Daytona server.
        target: The target environment for Daytona.
        custom_commands: Custom commands to run in the workspace.
        synchronous: If True, wait for the pipeline to complete. If False,
            return immediately after starting the pipeline. Defaults to False.
        image: Custom Docker image to use for the workspace.
        os_user: Operating system user for the workspace.
        env_vars: Additional environment variables to set in the workspace.
        labels: Labels to attach to the workspace.
        public: Whether the workspace should be public.
        cpu: Number of CPUs to allocate to the workspace.
        memory: Memory in MB to allocate to the workspace.
        disk: Disk size in GB to allocate to the workspace.
        gpu: Number of GPUs to allocate to the workspace.
        timeout: Timeout in seconds for workspace operations.
        auto_stop_interval: Interval in seconds after which to automatically stop the workspace.
    """

    # Authentication and connection settings
    api_key: Optional[str] = SecretField(default=None)
    server_url: Optional[str] = "https://daytona.work/api"
    target: Optional[str] = "us"
    custom_commands: Optional[List[str]] = None
    synchronous: bool = False

    # Workspace configuration
    image: Optional[str] = None
    os_user: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None
    public: Optional[bool] = None

    # Resource configuration
    cpu: Optional[int] = None
    memory: Optional[int] = None  # in MB
    disk: Optional[int] = None  # in GB
    gpu: Optional[int] = None

    # Operational settings
    timeout: Optional[float] = None
    auto_stop_interval: Optional[int] = None


class DaytonaOrchestratorConfig(
    BaseOrchestratorConfig, DaytonaOrchestratorSettings
):
    """Configuration for the Daytona orchestrator."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return False

    @property
    def supports_client_side_caching(self) -> bool:
        """Whether the orchestrator supports client side caching.

        Returns:
            Whether the orchestrator supports client side caching.
        """
        return False


class DaytonaOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Daytona orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DAYTONA_ORCHESTRATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/daytona.png"

    @property
    def config_class(self) -> Type[DaytonaOrchestratorConfig]:
        """Returns DaytonaOrchestratorConfig config class.

        Returns:
            The config class.
        """
        return DaytonaOrchestratorConfig

    @property
    def implementation_class(self) -> Type["DaytonaOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.daytona.orchestrators.daytona_orchestrator import (
            DaytonaOrchestrator,
        )

        return DaytonaOrchestrator
