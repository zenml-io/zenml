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
"""Vertex step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp import (
    GCP_RESOURCE_TYPE,
    GCP_VERTEX_STEP_OPERATOR_FLAVOR,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.integrations.gcp.vertex_custom_job_parameters import (
    VertexCustomJobParameters,
)
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.gcp.step_operators import VertexStepOperator


class VertexStepOperatorSettings(VertexCustomJobParameters, BaseSettings):
    """Settings for the Vertex step operator."""


class VertexStepOperatorConfig(
    BaseStepOperatorConfig,
    GoogleCredentialsConfigMixin,
    VertexStepOperatorSettings,
):
    """Configuration for the Vertex step operator.

    Attributes:
        region: Region name, e.g., `europe-west1`.
        encryption_spec_key_name: Encryption spec key name.
        network: The full name of the Compute Engine network to which the Job should be peered.
            For example, projects/12345/global/networks/myVPC
        reserved_ip_ranges: A list of names for the reserved ip ranges under the VPC network that can be used
            for this job. If set, we will deploy the job within the provided ip ranges. Otherwise, the job
            will be deployed to any ip ranges under the provided VPC network.
        service_account: Specifies the service account for workload run-as account. Users submitting jobs
            must have act-as permission on this run-as account.
    """

    region: str

    # customer managed encryption key resource name
    # will be applied to all Vertex AI resources if set
    encryption_spec_key_name: Optional[str] = None

    network: Optional[str] = None

    reserved_ip_ranges: Optional[str] = None

    service_account: Optional[str] = None

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


class VertexStepOperatorFlavor(BaseStepOperatorFlavor):
    """Vertex Step Operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            Name of the flavor.
        """
        return GCP_VERTEX_STEP_OPERATOR_FLAVOR

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
            resource_type=GCP_RESOURCE_TYPE,
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/vertexai.png"

    @property
    def config_class(self) -> Type[VertexStepOperatorConfig]:
        """Returns `VertexStepOperatorConfig` config class.

        Returns:
                The config class.
        """
        return VertexStepOperatorConfig

    @property
    def implementation_class(self) -> Type["VertexStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.step_operators import VertexStepOperator

        return VertexStepOperator
