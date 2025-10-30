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
"""Implementation of the AzureML Orchestrator flavor."""

from typing import TYPE_CHECKING

from pydantic import Field

from zenml.integrations.azure import (
    AZURE_RESOURCE_TYPE,
    AZUREML_ORCHESTRATOR_FLAVOR,
)
from zenml.integrations.azure.flavors.azureml import AzureMLComputeSettings
from zenml.logger import get_logger
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.azure.orchestrators import AzureMLOrchestrator

logger = get_logger(__name__)


class AzureMLOrchestratorSettings(AzureMLComputeSettings):
    """Settings for the AzureML orchestrator."""

    synchronous: bool = Field(
        default=True,
        description="Whether the orchestrator runs synchronously or not.",
    )


class AzureMLOrchestratorConfig(
    BaseOrchestratorConfig, AzureMLOrchestratorSettings
):
    """Configuration for the AzureML orchestrator."""

    subscription_id: str = Field(
        description="Subscription ID that AzureML is running on."
    )
    resource_group: str = Field(
        description="Name of the resource group that AzureML is running on.",
    )
    workspace: str = Field(
        description="Name of the workspace that AzureML is running on."
    )

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
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronously or not.

        Returns:
            Whether the orchestrator runs synchronously or not.
        """
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return True


class AzureMLOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the AzureML orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AZUREML_ORCHESTRATOR_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> ServiceConnectorRequirements | None:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(resource_type=AZURE_RESOURCE_TYPE)

    @property
    def docs_url(self) -> str | None:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> str | None:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/azureml.png"

    @property
    def config_class(self) -> type[AzureMLOrchestratorConfig]:
        """Returns AzureMLOrchestratorConfig config class.

        Returns:
            The config class.
        """
        return AzureMLOrchestratorConfig

    @property
    def implementation_class(self) -> type["AzureMLOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.azure.orchestrators import AzureMLOrchestrator

        return AzureMLOrchestrator
