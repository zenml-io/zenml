#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""AzureML step operator flavor."""

from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from zenml.integrations.azure import (
    AZURE_RESOURCE_TYPE,
    AZUREML_STEP_OPERATOR_FLAVOR,
)
from zenml.integrations.azure.flavors.azureml import (
    AzureMLComputeSettings,
    AzureMLComputeTypes,
)
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.azure.step_operators import AzureMLStepOperator


class AzureMLStepOperatorSettings(AzureMLComputeSettings):
    """Settings for the AzureML step operator.

    Attributes:
        compute_target_name: The name of the configured ComputeTarget.
            Deprecated in favor of `compute_name`.
    """

    compute_target_name: str | None = Field(
        default=None,
        description="Name of the configured ComputeTarget. Deprecated in favor "
        "of `compute_name`.",
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _migrate_compute_name(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Backward compatibility for compute_target_name.

        Args:
            data: The model data.

        Returns:
            The migrated data.
        """
        if (
            "compute_target_name" in data
            and "compute_name" not in data
            and "mode" not in data
        ):
            data["compute_name"] = data.pop("compute_target_name")
            data["mode"] = AzureMLComputeTypes.COMPUTE_INSTANCE

        return data


class AzureMLStepOperatorConfig(
    BaseStepOperatorConfig, AzureMLStepOperatorSettings
):
    """Config for the AzureML step operator.

    Attributes:
        subscription_id: The Azure account's subscription ID
        resource_group: The resource group to which the AzureML workspace
            is deployed.
        workspace_name: The name of the AzureML Workspace.
        tenant_id: The Azure Tenant ID.
        service_principal_id: The ID for the service principal that is created
            to allow apps to access secure resources.
        service_principal_password: Password for the service principal.
    """

    subscription_id: str = Field(
        description="Subscription ID that AzureML is running on."
    )
    resource_group: str = Field(
        description="Name of the resource group that AzureML is running on.",
    )
    workspace_name: str = Field(
        description="Name of the workspace that AzureML is running on."
    )

    # Service principal authentication
    # https://docs.microsoft.com/en-us/azure/machine-learning/how-to-setup-authentication#configure-a-service-principal
    tenant_id: str | None = SecretField(default=None)
    service_principal_id: str | None = SecretField(default=None)
    service_principal_password: str | None = SecretField(default=None)

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


class AzureMLStepOperatorFlavor(BaseStepOperatorFlavor):
    """Flavor for the AzureML step operator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AZUREML_STEP_OPERATOR_FLAVOR

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
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> str | None:
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/azureml.png"

    @property
    def config_class(self) -> type[AzureMLStepOperatorConfig]:
        """Returns AzureMLStepOperatorConfig config class.

        Returns:
                The config class.
        """
        return AzureMLStepOperatorConfig

    @property
    def implementation_class(self) -> type["AzureMLStepOperator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.azure.step_operators import AzureMLStepOperator

        return AzureMLStepOperator
