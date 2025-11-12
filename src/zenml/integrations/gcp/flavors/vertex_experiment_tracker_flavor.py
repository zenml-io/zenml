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
"""Vertex experiment tracker flavor."""

import re
from typing import TYPE_CHECKING, Any

from pydantic import Field, field_validator

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.gcp import (
    GCP_RESOURCE_TYPE,
    GCP_VERTEX_EXPERIMENT_TRACKER_FLAVOR,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.models import ServiceConnectorRequirements
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.gcp.experiment_trackers import (
        VertexExperimentTracker,
    )


class VertexExperimentTrackerSettings(BaseSettings):
    """Settings for the VertexAI experiment tracker."""

    experiment: str | None = Field(
        None, description="The VertexAI experiment name."
    )
    experiment_tensorboard: str | bool | None = Field(
        None,
        description="The VertexAI experiment tensorboard instance to use.",
    )

    @field_validator("experiment", mode="before")
    def _validate_experiment(cls, value: str) -> str:
        """Validates the experiment name matches the the allowed format.

        Args:
            value: The experiment.

        Raises:
            ValueError: If the experiment name does not match the expected
                format.

        Returns:
            The experiment.
        """
        if value and not re.match(r"^[a-z0-9][a-z0-9-]{0,127}$", value):
            raise ValueError(
                "Experiment name must match regex [a-z0-9][a-z0-9-]{0,127}"
            )
        return value


class VertexExperimentTrackerConfig(
    BaseExperimentTrackerConfig,
    GoogleCredentialsConfigMixin,
    VertexExperimentTrackerSettings,
):
    """Config for the VertexAI experiment tracker."""

    location: str | None = None
    staging_bucket: str | None = None
    network: str | None = None
    encryption_spec_key_name: str | None = SecretField(default=None)
    api_endpoint: str | None = SecretField(default=None)
    api_key: str | None = SecretField(default=None)
    api_transport: str | None = None
    request_metadata: dict[str, Any] | None = None


class VertexExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Flavor for the VertexAI experiment tracker."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GCP_VERTEX_EXPERIMENT_TRACKER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/experiment_tracker/vertexai.png"

    @property
    def config_class(self) -> type[VertexExperimentTrackerConfig]:
        """Returns `VertexExperimentTrackerConfig` config class.

        Returns:
            The config class.
        """
        return VertexExperimentTrackerConfig

    @property
    def implementation_class(self) -> type["VertexExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.experiment_trackers import (
            VertexExperimentTracker,
        )

        return VertexExperimentTracker

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
        return ServiceConnectorRequirements(
            resource_type=GCP_RESOURCE_TYPE,
        )
