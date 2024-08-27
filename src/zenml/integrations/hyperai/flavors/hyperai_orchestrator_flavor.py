#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the ZenML HyperAI orchestrator."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.hyperai import HYPERAI_RESOURCE_TYPE
from zenml.logger import get_logger
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.hyperai.orchestrators import HyperAIOrchestrator

logger = get_logger(__name__)


class HyperAIOrchestratorSettings(BaseSettings):
    """HyperAI orchestrator settings.

    Attributes:
        mounts_from_to: A dictionary mapping from paths on the HyperAI instance
            to paths within the Docker container. This allows users to mount
            directories from the HyperAI instance into the Docker container that runs
            on it.
    """

    mounts_from_to: Dict[str, str] = {}


class HyperAIOrchestratorConfig(
    BaseOrchestratorConfig, HyperAIOrchestratorSettings
):
    """Configuration for the HyperAI orchestrator.

    Attributes:
        container_registry_autologin: If True, the orchestrator will attempt to
            automatically log in to the container registry specified in the stack
            configuration on the HyperAI instance. This is useful if the container
            registry requires authentication and the HyperAI instance has not been
            manually logged in to the container registry. Defaults to `False`.
        automatic_cleanup_pipeline_files: If True, the orchestrator will
            automatically clean up old pipeline files that are on the HyperAI
            instance. Pipeline files will be cleaned up if they are 7 days old or
            older. Defaults to `True`.
        gpu_enabled_in_container: If True, the orchestrator will enable GPU
            support in the Docker container that runs on the HyperAI instance.
            Defaults to `True`.

    """

    container_registry_autologin: bool = False
    automatic_cleanup_pipeline_files: bool = True
    gpu_enabled_in_container: bool = True

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return True


class HyperAIOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the HyperAI orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return "hyperai"

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(
            resource_type=HYPERAI_RESOURCE_TYPE
        )

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/hyperai/hyperai.png"

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return HyperAIOrchestratorConfig

    @property
    def implementation_class(self) -> Type["HyperAIOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.hyperai.orchestrators import (
            HyperAIOrchestrator,
        )

        return HyperAIOrchestrator
