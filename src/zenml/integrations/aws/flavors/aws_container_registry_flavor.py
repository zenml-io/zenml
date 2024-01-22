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
"""AWS container registry flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import validator

from zenml.constants import DOCKER_REGISTRY_RESOURCE_TYPE
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistryConfig,
    BaseContainerRegistryFlavor,
)
from zenml.integrations.aws import (
    AWS_CONNECTOR_TYPE,
    AWS_CONTAINER_REGISTRY_FLAVOR,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.aws.container_registries import (
        AWSContainerRegistry,
    )


class AWSContainerRegistryConfig(BaseContainerRegistryConfig):
    """Configuration for AWS Container Registry."""

    @validator("uri")
    def validate_aws_uri(cls, uri: str) -> str:
        """Validates that the URI is in the correct format.

        Args:
            uri: URI to validate.

        Returns:
            URI in the correct format.

        Raises:
            ValueError: If the URI contains a slash character.
        """
        if "/" in uri:
            raise ValueError(
                "Property `uri` can not contain a `/`. An example of a valid "
                "URI is: `715803424592.dkr.ecr.us-east-1.amazonaws.com`"
            )

        return uri


class AWSContainerRegistryFlavor(BaseContainerRegistryFlavor):
    """AWS Container Registry flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AWS_CONTAINER_REGISTRY_FLAVOR

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
            connector_type=AWS_CONNECTOR_TYPE,
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            resource_id_attr="uri",
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/aws.png"

    @property
    def config_class(self) -> Type[AWSContainerRegistryConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return AWSContainerRegistryConfig

    @property
    def implementation_class(self) -> Type["AWSContainerRegistry"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.aws.container_registries import (
            AWSContainerRegistry,
        )

        return AWSContainerRegistry
