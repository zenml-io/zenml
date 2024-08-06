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

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.azure import (
    AZURE_RESOURCE_TYPE,
    AZUREML_ORCHESTRATOR_FLAVOR,
)
from zenml.logger import get_logger
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from zenml.integrations.azure.orchestrators import AzureMLOrchestrator

logger = get_logger(__name__)


class AzureMLComputeTypes(StrEnum):
    """Enum for different types of compute on AzureML."""

    SERVERLESS = "serverless"
    COMPUTE_INSTANCE = "compute-instance"
    COMPUTE_CLUSTER = "compute-cluster"


class AzureMLOrchestratorSettings(BaseSettings):
    """Settings for the AzureML orchestrator.

    These settings adjust the compute resources that will be used by the
    pipeline execution.

    There are three possible use cases for this implementation:

        1. Serverless compute (default behaviour):
            - The `mode` is set to `serverless` (default behaviour).
            - All the other parameters become irrelevant and will throw a
              warning if set.

        2. Compute instance:
            - The `mode` is set to `compute-instance`.
            - In this case, users have to provide a `compute-name`.
                - If a compute instance exists with this name, this instance
                will be used and all the other parameters become irrelevant
                and will throw a warning if set.
                - If a compute instance does not already exist, ZenML will
                create it. You can use the parameters `compute_size` and
                `idle_type_before_shutdown_minutes` for this operation.

        3. Compute cluster:
            - The `mode` is set to `compute-cluster`.
            - In this case, users have to provide a `compute-name`.
                - If a compute cluster exists with this name, this instance
                will be used and all the other parameters become irrelevant
                and will throw a warning if set.
                - If a compute cluster does not already exist, ZenML will
                create it. You can all the additional parameters for this
                operation.
    """

    # Mode for compute
    mode: AzureMLComputeTypes = AzureMLComputeTypes.SERVERLESS

    # Common Configuration for Compute Instances and Clusters
    compute_name: Optional[str] = None
    size: Optional[str] = None

    # Additional configuration for a Compute Instance
    idle_time_before_shutdown_minutes: Optional[int] = None

    # Additional configuration for a Compute Cluster
    idle_time_before_scaledown_down: Optional[int] = None
    location: Optional[str] = None
    min_instances: Optional[int] = None
    max_instances: Optional[int] = None
    tier: Optional[str] = None

    @model_validator(mode="after")
    def azureml_settings_validator(self) -> "AzureMLOrchestratorSettings":
        """Checks whether the right configuration is set based on mode.

        Returns:
            the instance itself.
        """
        viable_configuration_fields = {
            AzureMLComputeTypes.SERVERLESS: {"mode"},
            AzureMLComputeTypes.COMPUTE_INSTANCE: {
                "mode",
                "compute_name",
                "size",
                "idle_time_before_shutdown_minutes",
            },
            AzureMLComputeTypes.COMPUTE_CLUSTER: {
                "mode",
                "compute_name",
                "size",
                "idle_time_before_scaledown_down",
                "location",
                "min_instances",
                "max_instances",
                "tier",
            },
        }
        viable_fields = viable_configuration_fields[self.mode]

        for field in self.model_fields_set:
            if field not in viable_fields:
                logger.warning(
                    "In the AzureML Orchestrator Settings, the mode of "
                    f"operation is set to {self.mode}. In this mode, you can "
                    f"not configure the parameter '{field}'. This "
                    "configuration will be ignored."
                )

        return self


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
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/azureml.png"

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
