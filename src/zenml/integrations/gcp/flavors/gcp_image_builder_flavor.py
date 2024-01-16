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
"""Google Cloud image builder flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import PositiveInt

from zenml.image_builders import BaseImageBuilderConfig, BaseImageBuilderFlavor
from zenml.integrations.gcp import (
    GCP_CONNECTOR_TYPE,
    GCP_IMAGE_BUILDER_FLAVOR,
    GCP_RESOURCE_TYPE,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.gcp.image_builders import GCPImageBuilder

DEFAULT_CLOUD_BUILDER_IMAGE = "gcr.io/cloud-builders/docker"
DEFAULT_CLOUD_BUILDER_NETWORK = "cloudbuild"
DEFAULT_CLOUD_BUILD_TIMEOUT = 3600


class GCPImageBuilderConfig(
    BaseImageBuilderConfig, GoogleCredentialsConfigMixin
):
    """Google Cloud Builder image builder configuration.

    Attributes:
        cloud_builder_image: The name of the Docker image to use for the build
            steps. Defaults to `gcr.io/cloud-builders/docker`.
        network: The network name to which the build container will be
            attached while building the Docker image. More information about
            this:
            https://cloud.google.com/build/docs/build-config-file-schema#network.
            Defaults to `cloudbuild`.
        build_timeout: The timeout of the build in seconds. More information
            about this parameter:
            https://cloud.google.com/build/docs/build-config-file-schema#timeout_2
            Defaults to `3600`.
    """

    cloud_builder_image: str = DEFAULT_CLOUD_BUILDER_IMAGE
    network: str = DEFAULT_CLOUD_BUILDER_NETWORK
    build_timeout: PositiveInt = DEFAULT_CLOUD_BUILD_TIMEOUT


class GCPImageBuilderFlavor(BaseImageBuilderFlavor):
    """Google Cloud Builder image builder flavor."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The name of the flavor.
        """
        return GCP_IMAGE_BUILDER_FLAVOR

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
            connector_type=GCP_CONNECTOR_TYPE,
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/image_builder/gcp.png"

    @property
    def config_class(self) -> Type[BaseImageBuilderConfig]:
        """The config class.

        Returns:
            The config class.
        """
        return GCPImageBuilderConfig

    @property
    def implementation_class(self) -> Type["GCPImageBuilder"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.image_builders import GCPImageBuilder

        return GCPImageBuilder
