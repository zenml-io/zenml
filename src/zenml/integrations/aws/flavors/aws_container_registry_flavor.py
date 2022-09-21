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

from typing import TYPE_CHECKING, Type

from pydantic import validator

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistryConfig,
    BaseContainerRegistryFlavor,
)
from zenml.integrations.aws import AWS_CONTAINER_REGISTRY_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.aws.container_registries import AWSContainerRegistry


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
