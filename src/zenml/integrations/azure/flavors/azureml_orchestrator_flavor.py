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

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.azure import (
    AZURE_RESOURCE_TYPE,
    AZUREML_ORCHESTRATOR_FLAVOR,
)
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.azure.orchestrators import AzureMLOrchestrator


class AzureMLOrchestratorSettings(BaseSettings):
    """Settings for the AzureML orchestrator."""

    compute_target: str = Field(
        description="The name of the compute target to either use or create."
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

    # Service principal authentication
    # https://docs.microsoft.com/en-us/azure/machine-learning/how-to-setup-authentication#configure-a-service-principal
    tenant_id: Optional[str] = SecretField(default=None)
    service_principal_id: Optional[str] = SecretField(default=None)
    service_principal_password: Optional[str] = SecretField(default=None)

    @property
    def is_remote(self) -> bool:
        return True

    @property
    def is_synchronous(self) -> bool:
        return False


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
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(resource_type=AZURE_RESOURCE_TYPE)

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/azureml.png"

    @property
    def config_class(self) -> Type[AzureMLOrchestratorConfig]:
        """Returns AzureMLOrchestratorConfig config class.

        Returns:
            The config class.
        """
        return AzureMLOrchestratorConfig

    @property
    def implementation_class(self) -> Type["AzureMLOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.azure.orchestrators import AzureMLOrchestrator

        return AzureMLOrchestrator
