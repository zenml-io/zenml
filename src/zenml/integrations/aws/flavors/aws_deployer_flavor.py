#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""AWS App Runner deployer flavor."""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type

from pydantic import Field

from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.integrations.aws import (
    AWS_CONNECTOR_TYPE,
    AWS_DEPLOYER_FLAVOR,
    AWS_RESOURCE_TYPE,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.aws.deployers import AWSDeployer


class AWSDeployerSettings(BaseDeployerSettings):
    """Settings for the AWS App Runner deployer."""

    region: Optional[str] = Field(
        default=None,
        description="AWS region where the App Runner service will be deployed. "
        "If not specified, the region will be determined from the authenticated "
        "session (service connector or implicit credentials). "
        "App Runner is available in specific regions: "
        "https://docs.aws.amazon.com/apprunner/latest/dg/regions.html",
    )
    service_name_prefix: str = Field(
        default="zenml-",
        description="Prefix for service names in App Runner to avoid naming "
        "conflicts.",
    )

    # Health check configuration
    health_check_grace_period_seconds: int = Field(
        default=20,
        ge=0,
        le=20,
        description="Grace period for health checks in seconds. Range: 0-20.",
    )

    health_check_interval_seconds: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Interval between health checks in seconds. Range: 1-20.",
    )

    health_check_protocol: str = Field(
        default="TCP",
        description="Health check protocol. Options: 'TCP', 'HTTP'.",
        pattern="^TCP|HTTP$",
    )

    health_check_timeout_seconds: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Timeout for health checks in seconds. Range: 1-20.",
    )

    health_check_healthy_threshold: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Number of consecutive successful health checks required.",
    )

    health_check_unhealthy_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of consecutive failed health checks before unhealthy.",
    )

    # Networking and security
    is_publicly_accessible: bool = Field(
        default=True,
        description="Whether the App Runner service is publicly accessible.",
    )

    ingress_vpc_configuration: Optional[str] = Field(
        default=None,
        description="VPC configuration for private App Runner services. "
        "JSON string with VpcId, VpcEndpointId, and VpcIngressConnectionName.",
    )

    # Environment and configuration
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the App Runner service.",
    )

    # Tags
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Tags to apply to the App Runner service.",
    )

    # Secret management configuration
    use_secrets_manager: bool = Field(
        default=True,
        description="Whether to store sensitive environment variables in AWS "
        "Secrets Manager instead of directly in the App Runner service "
        "configuration.",
    )

    secret_name_prefix: str = Field(
        default="zenml-",
        description="Prefix for secret names in Secrets Manager to avoid naming "
        "conflicts.",
    )

    # Observability
    observability_configuration_arn: Optional[str] = Field(
        default=None,
        description="ARN of the observability configuration to associate with "
        "the App Runner service.",
    )

    # Encryption
    encryption_kms_key: Optional[str] = Field(
        default=None,
        description="KMS key ARN for encrypting App Runner service data.",
    )

    # IAM Roles
    instance_role_arn: Optional[str] = Field(
        default=None,
        description="ARN of the IAM role to assign to the App Runner service instances.",
    )

    access_role_arn: Optional[str] = Field(
        default=None,
        description="ARN of the IAM role that App Runner uses to access the "
        "image repository (ECR). Required for private ECR repositories. If not "
        "specified, App Runner will attempt to use the default service role, "
        "which may not have ECR access permissions.",
    )

    # Traffic allocation for A/B testing and gradual rollouts
    traffic_allocation: Dict[str, int] = Field(
        default_factory=lambda: {"LATEST": 100},
        description="Traffic allocation between revisions for A/B testing and "
        "gradual rollouts. Keys can be revision names, tags, or 'LATEST' for "
        "the most recent revision. Values are percentages that must sum to 100. "
        "Example: {'LATEST': 80, 'my-stable-revision': 20}",
    )

    # Resource matching
    strict_resource_matching: bool = Field(
        default=False,
        description="Whether to enforce strict matching of resource requirements "
        "to AWS App Runner supported CPU (vCPU) and memory (GB) combinations. "
        "When True, raises an error if no exact match is found. When False, "
        "automatically selects the closest matching supported combination. "
        "See https://docs.aws.amazon.com/apprunner/latest/dg/architecture.html#architecture.vcpu-memory "
        "for more details.",
    )


# AWS App Runner supported CPU (vCPU) and memory (GB) combinations
DEFAULT_RESOURCE_COMBINATIONS = [
    (
        0.25,
        0.5,
    ),
    (
        0.25,
        1.0,
    ),
    (
        0.5,
        1.0,
    ),
    (
        1.0,
        2.0,
    ),
    (
        1.0,
        3.0,
    ),
    (
        1.0,
        4.0,
    ),
    (
        2.0,
        4.0,
    ),
    (
        2.0,
        6.0,
    ),
    (
        4.0,
        8.0,
    ),
    (
        4.0,
        10.0,
    ),
    (
        4.0,
        12.0,
    ),
]


class AWSDeployerConfig(
    BaseDeployerConfig,
    AWSDeployerSettings,
):
    """Configuration for the AWS App Runner deployer."""

    resource_combinations: List[Tuple[float, float]] = Field(
        default=DEFAULT_RESOURCE_COMBINATIONS,
        description="AWS App Runner supported CPU (vCPU), memory (GB) "
        "combinations.",
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


class AWSDeployerFlavor(BaseDeployerFlavor):
    """AWS App Runner deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the deployer flavor.

        Returns:
            Name of the deployer flavor.
        """
        return AWS_DEPLOYER_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the deployer flavor.

        Returns:
            The display name of the deployer flavor.
        """
        return "AWS"

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
            resource_type=AWS_RESOURCE_TYPE,
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/deployer/aws-app-runner.png"

    @property
    def config_class(self) -> Type[AWSDeployerConfig]:
        """Returns the AWSDeployerConfig config class.

        Returns:
                The config class.
        """
        return AWSDeployerConfig

    @property
    def implementation_class(self) -> Type["AWSDeployer"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.aws.deployers import AWSDeployer

        return AWSDeployer
