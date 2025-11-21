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
"""GCP Cloud Run deployer flavor."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from pydantic import Field

from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.integrations.gcp import (
    GCP_DEPLOYER_FLAVOR,
    GCP_RESOURCE_TYPE,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.gcp.deployers import GCPDeployer


class GCPDeployerSettings(BaseDeployerSettings):
    """Settings for the GCP Cloud Run deployer."""

    location: str = Field(
        default="europe-west3",
        description="Name of GCP region where the pipeline will be deployed. "
        "Cloud Run is available in specific regions: "
        "https://cloud.google.com/run/docs/locations",
    )
    service_name_prefix: str = Field(
        default="zenml-",
        description="Prefix for service names in Cloud Run to avoid naming "
        "conflicts.",
    )

    # Timeout and execution configuration
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Request timeout in seconds. Maximum is 3600 (1 hour).",
    )

    # Networking and security
    ingress: str = Field(
        default="all",
        description="Ingress settings for the service. "
        "Options: 'all', 'internal', 'internal-and-cloud-load-balancing'.",
    )

    vpc_connector: Optional[str] = Field(
        default=None,
        description="VPC connector for private networking. "
        "Format: projects/PROJECT_ID/locations/LOCATION/connectors/CONNECTOR_NAME",
    )

    # Service account and IAM
    service_account: Optional[str] = Field(
        default=None,
        description="Service account email to run the Cloud Run service. "
        "If not specified, uses the default Compute Engine service account.",
    )

    # Environment and configuration
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the Cloud Run service.",
    )

    # Labels and annotations
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to apply to the Cloud Run service.",
    )

    annotations: Dict[str, str] = Field(
        default_factory=dict,
        description="Annotations to apply to the Cloud Run service.",
    )

    # Cloud Run specific settings
    execution_environment: str = Field(
        default="gen2",
        description="Execution environment generation. Options: 'gen1', 'gen2'.",
    )

    # Deployment configuration
    traffic_allocation: Dict[str, int] = Field(
        default_factory=lambda: {"LATEST": 100},
        description="Traffic allocation between revisions. "
        "Keys are revision names or 'LATEST', values are percentages.",
    )

    allow_unauthenticated: bool = Field(
        default=True,
        description="Whether to allow unauthenticated requests to the service.",
    )

    # Secret management configuration
    use_secret_manager: bool = Field(
        default=True,
        description="Whether to store sensitive environment variables in GCP "
        "Secret Manager instead of directly in the Cloud Run service "
        "configuration.",
    )

    secret_name_prefix: str = Field(
        default="zenml-",
        description="Prefix for secret names in Secret Manager to avoid naming "
        "conflicts.",
    )


class GCPDeployerConfig(
    BaseDeployerConfig,
    GoogleCredentialsConfigMixin,
    GCPDeployerSettings,
):
    """Configuration for the GCP Cloud Run deployer."""

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


class GCPDeployerFlavor(BaseDeployerFlavor):
    """GCP Cloud Run deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return GCP_DEPLOYER_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "GCP"

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/deployer/google-cloud-run.svg"

    @property
    def config_class(self) -> Type[GCPDeployerConfig]:
        """Returns the GCPDeployerConfig config class.

        Returns:
                The config class.
        """
        return GCPDeployerConfig

    @property
    def implementation_class(self) -> Type["GCPDeployer"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.gcp.deployers import GCPDeployer

        return GCPDeployer
