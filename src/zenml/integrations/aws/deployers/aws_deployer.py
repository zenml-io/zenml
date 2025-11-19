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
"""Implementation of the AWS App Runner deployer."""

import datetime
import json
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from zenml.config.base_settings import BaseSettings
from zenml.config.resource_settings import ResourceSettings
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
    DeploymentLogsNotFoundError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.deployers.server.entrypoint_configuration import (
    DEPLOYMENT_ID_OPTION,
    DeploymentEntrypointConfiguration,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.integrations.aws.flavors.aws_deployer_flavor import (
    AWSDeployerConfig,
    AWSDeployerSettings,
)
from zenml.logger import get_logger
from zenml.models import (
    DeploymentOperationalState,
    DeploymentResponse,
)
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)

# Default resource and scaling configuration constants
DEFAULT_CPU = 0.25  # vCPU
DEFAULT_MEMORY = 0.5  # GB
DEFAULT_MIN_REPLICAS = 1
DEFAULT_MAX_REPLICAS = 25
DEFAULT_MAX_CONCURRENCY = 100

# AWS App Runner built-in limits
AWS_APP_RUNNER_MAX_SIZE = 1000
AWS_APP_RUNNER_MAX_CONCURRENCY = 1000


class AppRunnerDeploymentMetadata(BaseModel):
    """Metadata for an App Runner deployment."""

    service_name: Optional[str] = None
    service_arn: Optional[str] = None
    service_url: Optional[str] = None
    region: Optional[str] = None
    service_id: Optional[str] = None
    status: Optional[str] = None
    source_configuration: Optional[Dict[str, Any]] = None
    instance_configuration: Optional[Dict[str, Any]] = None
    auto_scaling_configuration_summary: Optional[Dict[str, Any]] = None
    auto_scaling_configuration_arn: Optional[str] = None
    health_check_configuration: Optional[Dict[str, Any]] = None
    network_configuration: Optional[Dict[str, Any]] = None
    observability_configuration: Optional[Dict[str, Any]] = None
    encryption_configuration: Optional[Dict[str, Any]] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None
    port: Optional[int] = None
    auto_scaling_max_concurrency: Optional[int] = None
    auto_scaling_max_size: Optional[int] = None
    auto_scaling_min_size: Optional[int] = None
    is_publicly_accessible: Optional[bool] = None
    health_check_grace_period_seconds: Optional[int] = None
    health_check_interval_seconds: Optional[int] = None
    health_check_path: Optional[str] = None
    health_check_protocol: Optional[str] = None
    health_check_timeout_seconds: Optional[int] = None
    health_check_healthy_threshold: Optional[int] = None
    health_check_unhealthy_threshold: Optional[int] = None
    tags: Optional[Dict[str, str]] = None
    traffic_allocation: Optional[Dict[str, int]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    secret_arn: Optional[str] = None

    @classmethod
    def from_app_runner_service(
        cls,
        service: Dict[str, Any],
        region: str,
        secret_arn: Optional[str] = None,
    ) -> "AppRunnerDeploymentMetadata":
        """Create metadata from an App Runner service.

        Args:
            service: The App Runner service dictionary from describe_service.
            region: The AWS region.
            secret_arn: The AWS Secrets Manager secret ARN for the deployment.

        Returns:
            The metadata for the App Runner service.
        """
        instance_config = service.get("InstanceConfiguration", {})
        cpu = instance_config.get("Cpu")
        memory = instance_config.get("Memory")

        auto_scaling_config = service.get(
            "AutoScalingConfigurationSummary", {}
        )
        auto_scaling_configuration_arn = auto_scaling_config.get(
            "AutoScalingConfigurationArn"
        )
        auto_scaling_max_concurrency = auto_scaling_config.get(
            "MaxConcurrency"
        )
        auto_scaling_max_size = auto_scaling_config.get("MaxSize")
        auto_scaling_min_size = auto_scaling_config.get("MinSize")

        health_check_config = service.get("HealthCheckConfiguration", {})
        health_check_grace_period = health_check_config.get(
            "HealthCheckGracePeriodSeconds"
        )
        health_check_interval = health_check_config.get("Interval")
        health_check_path = health_check_config.get("Path")
        health_check_protocol = health_check_config.get("Protocol")
        health_check_timeout = health_check_config.get("Timeout")
        health_check_healthy_threshold = health_check_config.get(
            "HealthyThreshold"
        )
        health_check_unhealthy_threshold = health_check_config.get(
            "UnhealthyThreshold"
        )

        network_config = service.get("NetworkConfiguration", {})
        is_publicly_accessible = network_config.get(
            "IngressConfiguration", {}
        ).get("IsPubliclyAccessible")

        source_config = service.get("SourceConfiguration", {})
        image_repo = source_config.get("ImageRepository", {})
        image_config = image_repo.get("ImageConfiguration", {})

        port = None
        if image_config:
            port = image_config.get("Port")

        traffic_allocation = {}
        traffic_config = service.get("TrafficConfiguration", [])
        for traffic in traffic_config:
            if traffic.get("Type") == "LATEST":
                traffic_allocation["LATEST"] = traffic.get("Percent", 0)
            elif traffic.get("Revision"):
                traffic_allocation[traffic["Revision"]] = traffic.get(
                    "Percent", 0
                )
            elif traffic.get("Tag"):
                traffic_allocation[f"tag:{traffic['Tag']}"] = traffic.get(
                    "Percent", 0
                )

        # Extract timestamps
        created_at = service.get("CreatedAt")
        updated_at = service.get("UpdatedAt")
        deleted_at = service.get("DeletedAt")

        return cls(
            service_name=service.get("ServiceName"),
            service_arn=service.get("ServiceArn"),
            service_url=service.get("ServiceUrl"),
            region=region,
            service_id=service.get("ServiceId"),
            status=service.get("Status"),
            source_configuration=source_config,
            instance_configuration=instance_config,
            auto_scaling_configuration_summary=auto_scaling_config,
            auto_scaling_configuration_arn=auto_scaling_configuration_arn,
            health_check_configuration=health_check_config,
            network_configuration=network_config,
            observability_configuration=service.get(
                "ObservabilityConfiguration"
            ),
            encryption_configuration=service.get("EncryptionConfiguration"),
            cpu=cpu,
            memory=memory,
            port=port,
            auto_scaling_max_concurrency=auto_scaling_max_concurrency,
            auto_scaling_max_size=auto_scaling_max_size,
            auto_scaling_min_size=auto_scaling_min_size,
            is_publicly_accessible=is_publicly_accessible,
            health_check_grace_period_seconds=health_check_grace_period,
            health_check_interval_seconds=health_check_interval,
            health_check_path=health_check_path,
            health_check_protocol=health_check_protocol,
            health_check_timeout_seconds=health_check_timeout,
            health_check_healthy_threshold=health_check_healthy_threshold,
            health_check_unhealthy_threshold=health_check_unhealthy_threshold,
            tags=dict(service.get("Tags", {})),
            traffic_allocation=traffic_allocation
            if traffic_allocation
            else None,
            created_at=created_at.isoformat() if created_at else None,
            updated_at=updated_at.isoformat() if updated_at else None,
            deleted_at=deleted_at.isoformat() if deleted_at else None,
            secret_arn=secret_arn,
        )

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "AppRunnerDeploymentMetadata":
        """Create metadata from a deployment.

        Args:
            deployment: The deployment to get the metadata for.

        Returns:
            The metadata for the deployment.
        """
        return cls.model_validate(deployment.deployment_metadata)


class AWSDeployer(ContainerizedDeployer):
    """Deployer responsible for deploying pipelines on AWS App Runner."""

    _boto_session: Optional[boto3.Session] = None
    _region: Optional[str] = None
    _app_runner_client: Optional[Any] = None
    _secrets_manager_client: Optional[Any] = None
    _logs_client: Optional[Any] = None

    @property
    def config(self) -> AWSDeployerConfig:
        """Returns the `AWSDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(AWSDeployerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AWS deployer.

        Returns:
            The settings class.
        """
        return AWSDeployerSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is an image builder in the stack.

        Returns:
            A `StackValidator` instance.
        """
        return StackValidator(
            required_components={
                StackComponentType.IMAGE_BUILDER,
                StackComponentType.CONTAINER_REGISTRY,
            }
        )

    def _get_boto_session_and_region(self) -> Tuple[boto3.Session, str]:
        """Get an authenticated boto3 session and determine the region.

        Returns:
            A tuple containing the boto3 session and the AWS region.

        Raises:
            RuntimeError: If the service connector returns an unexpected type.
        """
        if (
            self._boto_session is not None
            and self._region is not None
            and not self.connector_has_expired()
        ):
            return self._boto_session, self._region

        # Option 1: Service connector
        if connector := self.get_connector():
            boto_session = connector.connect()
            if not isinstance(boto_session, boto3.Session):
                raise RuntimeError(
                    f"Expected to receive a `boto3.Session` object from the "
                    f"linked connector, but got type `{type(boto_session)}`."
                )

            region = boto_session.region_name
            if not region:
                # Fallback to config region or default
                region = self.config.region or "us-east-1"
                logger.warning(
                    f"No region found in boto3 session, using {region}"
                )

        # Option 2: Implicit configuration
        else:
            boto_session = boto3.Session(region_name=self.config.region)

        self._boto_session = boto_session
        self._region = region
        return boto_session, region

    @property
    def app_runner_client(self) -> Any:
        """Get the App Runner client.

        Returns:
            The App Runner client.
        """
        if self._app_runner_client is None or self.connector_has_expired():
            session, region = self._get_boto_session_and_region()
            self._app_runner_client = session.client(
                "apprunner", region_name=region
            )
        return self._app_runner_client

    @property
    def secrets_manager_client(self) -> Any:
        """Get the Secrets Manager client.

        Returns:
            The Secrets Manager client.
        """
        if (
            self._secrets_manager_client is None
            or self.connector_has_expired()
        ):
            session, region = self._get_boto_session_and_region()
            self._secrets_manager_client = session.client(
                "secretsmanager", region_name=region
            )
        return self._secrets_manager_client

    @property
    def logs_client(self) -> Any:
        """Get the CloudWatch Logs client.

        Returns:
            The CloudWatch Logs client.
        """
        if self._logs_client is None or self.connector_has_expired():
            session, region = self._get_boto_session_and_region()
            self._logs_client = session.client("logs", region_name=region)
        return self._logs_client

    @property
    def region(self) -> str:
        """Get the AWS region.

        Returns:
            The AWS region.
        """
        _, region = self._get_boto_session_and_region()
        return region

    def get_tags(
        self,
        deployment: DeploymentResponse,
        settings: AWSDeployerSettings,
    ) -> List[Dict[str, str]]:
        """Get the tags for a deployment to be used for AWS resources.

        Args:
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            The tags for the deployment.
        """
        tags = {
            **settings.tags,
            "zenml-deployment-id": str(deployment.id),
            "zenml-deployment-name": deployment.name,
            "zenml-deployer-name": str(self.name),
            "zenml-deployer-id": str(self.id),
            "managed-by": "zenml",
        }

        return [{"Key": k, "Value": v} for k, v in tags.items()]

    def _sanitize_name(
        self,
        name: str,
        random_suffix: str,
        max_length: int = 32,
        extra_allowed_characters: str = "-_",
    ) -> str:
        """Sanitize a name to comply with AWS naming requirements.

        Common AWS naming requirements:
        - Length: 4-max_length characters
        - Characters: letters (a-z, A-Z), numbers (0-9), configured extra
        allowed characters (e.g. dashes and underscores)
        - Must start and end with a letter or number
        - Cannot contain consecutive extra_allowed_characters

        Args:
            name: The raw name to sanitize.
            random_suffix: A random suffix to add to the name to ensure
                uniqueness.
            max_length: The maximum length of the name.
            extra_allowed_characters: Extra allowed characters in the name.

        Returns:
            A sanitized name that complies with AWS requirements.

        Raises:
            RuntimeError: If the random suffix is invalid.
            ValueError: If the service name is invalid.
        """
        if (
            not re.match(r"^[a-zA-Z0-9]+$", random_suffix)
            or len(random_suffix) < 4
        ):
            raise RuntimeError(
                f"Invalid random suffix: {random_suffix}. Must contain only "
                "letters and numbers and be at least 4 characters long."
            )

        # Use the first extra allowed character as the separator
        separator = extra_allowed_characters[0]

        # Replace all disallowed characters with the separator
        sanitized = re.sub(
            rf"[^a-zA-Z0-9{extra_allowed_characters}]",
            separator,
            name,
        )

        # Remove consecutive extra allowed characters
        for char in extra_allowed_characters:
            sanitized = re.sub(
                rf"[{char}]+",
                char,
                sanitized,
            )

        # Remove leading and trailing extra allowed characters before truncating
        sanitized = re.sub(
            r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$",
            "",
            sanitized,
        )

        # Truncate to fit within max_length character limit including suffix
        max_base_length = (
            max_length - len(random_suffix) - 1
        )  # -1 for the separator
        if len(sanitized) > max_base_length:
            sanitized = sanitized[:max_base_length]

        # Ensure it starts and ends with alphanumeric characters
        sanitized = re.sub(
            r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$",
            "",
            sanitized,
        )

        # Ensure we have at least one character after cleanup
        if not sanitized:
            raise ValueError(
                f"Invalid name: {name}. Must contain at least one "
                "alphanumeric character."
            )

        return f"{sanitized}{separator}{random_suffix}"

    def _get_service_name(
        self, deployment_name: str, deployment_id: UUID, prefix: str
    ) -> str:
        """Get the App Runner service name for a deployment.

        Args:
            deployment_name: The deployment name.
            deployment_id: The deployment ID.
            prefix: The prefix to use for the service name.

        Returns:
            The App Runner service name that complies with all naming
            requirements.
        """
        # We use the first 8 characters of the deployment UUID as a random
        # suffix to ensure uniqueness.
        deployment_id_short = str(deployment_id)[:8]
        raw_name = f"{prefix}{deployment_name}"

        return self._sanitize_name(
            raw_name,
            random_suffix=deployment_id_short,
            max_length=40,
            extra_allowed_characters="-_",
        )

    def _get_secret_name(
        self,
        deployment_name: str,
        deployment_id: UUID,
        prefix: str,
    ) -> str:
        """Get the Secrets Manager secret name for a deployment.

        Args:
            deployment_name: The deployment name.
            deployment_id: The deployment ID.
            prefix: The prefix to use for the secret name.

        Returns:
            The Secrets Manager secret name.
        """
        # We use the first 8 characters of the deployment UUID as a random
        # suffix to ensure uniqueness.
        deployment_id_short = str(deployment_id)[:8]
        raw_name = f"{prefix}{deployment_name}"

        return self._sanitize_name(
            raw_name,
            random_suffix=deployment_id_short,
            max_length=512,
            extra_allowed_characters="-_./",
        )

    def _create_or_update_secret(
        self,
        secret_name: str,
        secret_value: str,
        deployment: DeploymentResponse,
        settings: AWSDeployerSettings,
    ) -> str:
        """Create or update a secret in Secrets Manager.

        Args:
            secret_name: The name of the secret.
            secret_value: The value to store.
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            The secret ARN.

        Raises:
            ClientError: If the secret cannot be updated.
            DeployerError: If secret creation/update fails.
        """
        try:
            try:
                response = self.secrets_manager_client.update_secret(
                    SecretId=secret_name,
                    SecretString=secret_value,
                )
                self.secrets_manager_client.tag_resource(
                    SecretId=response["ARN"],
                    Tags=self.get_tags(deployment, settings),
                )
                logger.debug(f"Updated existing secret {secret_name}")
                return response["ARN"]  # type: ignore[no-any-return]
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    logger.debug(f"Creating new secret {secret_name}")
                    response = self.secrets_manager_client.create_secret(
                        Name=secret_name,
                        SecretString=secret_value,
                        Description=f"ZenML deployment secret for {deployment.name}",
                        Tags=self.get_tags(deployment, settings),
                    )
                    logger.debug(f"Created new secret {secret_name}")
                    return response["ARN"]  # type: ignore[no-any-return]
                else:
                    raise

        except (ClientError, BotoCoreError) as e:
            raise DeployerError(
                f"Failed to create/update secret {secret_name}: {e}"
            )

    def _get_secret_arn(self, deployment: DeploymentResponse) -> Optional[str]:
        """Get the existing AWS Secrets Manager secret ARN for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The existing AWS Secrets Manager secret ARN for the deployment,
            or None if no secret exists.
        """
        metadata = AppRunnerDeploymentMetadata.from_deployment(deployment)

        if not metadata.secret_arn:
            return None

        try:
            self.secrets_manager_client.describe_secret(
                SecretId=metadata.secret_arn
            )
            return metadata.secret_arn
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            logger.exception(f"Failed to verify secret {metadata.secret_arn}")
            return None

    def _delete_secret(self, secret_arn: str) -> None:
        """Delete a secret from Secrets Manager.

        Args:
            secret_arn: The ARN of the secret to delete.
        """
        try:
            self.secrets_manager_client.delete_secret(
                SecretId=secret_arn,
                ForceDeleteWithoutRecovery=True,
            )
            logger.debug(f"Deleted secret {secret_arn}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.debug(
                    f"Secret {secret_arn} not found, skipping deletion"
                )
            else:
                logger.exception(f"Failed to delete secret {secret_arn}")

    def _cleanup_deployment_secrets(
        self,
        deployment: DeploymentResponse,
    ) -> None:
        """Clean up the secret associated with a deployment.

        Args:
            deployment: The deployment.
        """
        secret_arn = self._get_secret_arn(deployment)

        if secret_arn:
            self._delete_secret(secret_arn)

    def _get_auto_scaling_config_name(
        self, deployment_name: str, deployment_id: UUID
    ) -> str:
        """Get the auto-scaling configuration name for a deployment.

        Args:
            deployment_name: The deployment name.
            deployment_id: The deployment ID.

        Returns:
            The auto-scaling configuration name.
        """
        # We use the first 8 characters of the deployment UUID as a random
        # suffix to ensure uniqueness.
        deployment_id_short = str(deployment_id)[:8]
        raw_name = f"zenml-{deployment_name}-{deployment_id_short}"

        return self._sanitize_name(
            raw_name,
            random_suffix=deployment_id_short,
            max_length=32,
            extra_allowed_characters="-_",
        )

    def _create_or_update_auto_scaling_config(
        self,
        config_name: str,
        min_size: int,
        max_size: int,
        max_concurrency: int,
        deployment: DeploymentResponse,
        settings: AWSDeployerSettings,
    ) -> str:
        """Create or update an auto-scaling configuration for App Runner.

        Args:
            config_name: The name for the auto-scaling configuration.
            min_size: Minimum number of instances.
            max_size: Maximum number of instances.
            max_concurrency: Maximum concurrent requests per instance.
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            The ARN of the created/updated auto-scaling configuration.

        Raises:
            ClientError: If the auto-scaling configuration cannot be described.
            DeployerError: If auto-scaling configuration creation/update fails.
        """
        try:
            metadata = AppRunnerDeploymentMetadata.from_deployment(deployment)
            existing_arn = metadata.auto_scaling_configuration_arn

            if existing_arn:
                try:
                    response = self.app_runner_client.describe_auto_scaling_configuration(
                        AutoScalingConfigurationArn=existing_arn
                    )
                    existing_config = response["AutoScalingConfiguration"]

                    if (
                        existing_config["MaxConcurrency"] == max_concurrency
                        and existing_config["MaxSize"] == max_size
                        and existing_config["MinSize"] == min_size
                    ):
                        logger.debug(
                            f"Auto-scaling configuration {existing_arn} is up "
                            "to date"
                        )
                        return existing_arn

                    logger.debug(
                        f"Auto-scaling configuration {existing_arn} is out of "
                        "date, updating it"
                    )

                except ClientError as e:
                    if (
                        e.response["Error"]["Code"]
                        != "InvalidRequestException"
                    ):
                        raise
                    logger.debug(
                        f"Existing auto-scaling configuration {existing_arn} "
                        "not found, creating new one"
                    )
            else:
                logger.debug(
                    f"Creating auto-scaling configuration {config_name}"
                )

            # The create_auto_scaling_configuration call is used to both create
            # a new auto-scaling configuration and update an existing one.
            # It is possible to create multiple revisions of the same
            # configuration by calling create_auto_scaling_configuration
            # multiple times using the same AutoScalingConfigurationName.
            response = (
                self.app_runner_client.create_auto_scaling_configuration(
                    AutoScalingConfigurationName=config_name,
                    MaxConcurrency=max_concurrency,
                    MaxSize=max_size,
                    MinSize=min_size,
                    Tags=self.get_tags(deployment, settings),
                )
            )

            return response["AutoScalingConfiguration"][  # type: ignore[no-any-return]
                "AutoScalingConfigurationArn"
            ]

        except (ClientError, BotoCoreError) as e:
            raise DeployerError(
                f"Failed to create/update auto-scaling configuration "
                f"{config_name}: {e}"
            )

    def _cleanup_deployment_auto_scaling_config(
        self, deployment: DeploymentResponse
    ) -> None:
        """Clean up the auto-scaling configuration associated with a deployment.

        Args:
            deployment: The deployment.
        """
        metadata = AppRunnerDeploymentMetadata.from_deployment(deployment)
        config_arn = metadata.auto_scaling_configuration_arn
        if not config_arn:
            return

        try:
            logger.debug(f"Deleting auto-scaling configuration {config_arn}")
            self.app_runner_client.delete_auto_scaling_configuration(
                AutoScalingConfigurationArn=config_arn
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.debug(
                    f"Auto-scaling configuration {config_arn} not found, "
                    "skipping deletion"
                )
            else:
                logger.warning(
                    f"Failed to delete auto-scaling configuration {config_arn}: "
                    f"{e}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to delete auto-scaling configuration {config_arn}: "
                f"{e}"
            )

    def _prepare_environment_variables(
        self,
        deployment: DeploymentResponse,
        environment: Dict[str, str],
        secrets: Dict[str, str],
        settings: AWSDeployerSettings,
    ) -> Tuple[Dict[str, str], Dict[str, str], Optional[str]]:
        """Prepare environment variables for App Runner, handling secrets appropriately.

        Args:
            deployment: The deployment.
            environment: Regular environment variables.
            secrets: Sensitive environment variables.
            settings: The deployer settings.

        Returns:
            Tuple containing:
            - Dictionary of regular environment variables.
            - Dictionary of secret environment variables (key -> secret ARN).
            - Optional secret ARN (None if no secrets or fallback to env vars).
        """
        secret_refs = {}
        active_secret_arn: Optional[str] = None

        env_vars = {**settings.environment_variables, **environment}

        if secrets:
            if settings.use_secrets_manager:
                # Always store secrets as single JSON secret and reference their
                # keys in the App Runner service configuration environment
                # variables.

                secret_name = self._get_secret_name(
                    deployment.name, deployment.id, settings.secret_name_prefix
                )

                try:
                    secret_value = json.dumps(secrets)
                    secret_arn = self._create_or_update_secret(
                        secret_name, secret_value, deployment, settings
                    )
                    active_secret_arn = secret_arn

                    for key in secrets.keys():
                        secret_refs[key] = f"{secret_arn}:{key}::"

                    logger.debug(
                        f"Secret {secret_name} stored with ARN {secret_arn} "
                        f"containing {len(secrets)} secret(s)"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to create secret, falling back "
                        f"to direct env vars: {e}"
                    )
                    env_vars.update(secrets)

                existing_secret_arn = self._get_secret_arn(deployment)
                if (
                    existing_secret_arn
                    and existing_secret_arn != active_secret_arn
                ):
                    # Sometimes the previous secret resource is different from
                    # the new secret resource, e.g. if the secret name changed.
                    # In this case, we need to delete the old secret resource.
                    self._delete_secret(existing_secret_arn)
            else:
                logger.warning(
                    "Storing secrets directly in environment variables. "
                    "Consider enabling use_secrets_manager for better security."
                )
                env_vars.update(secrets)

        return env_vars, secret_refs, active_secret_arn

    def _get_app_runner_service(
        self, deployment: DeploymentResponse
    ) -> Optional[Dict[str, Any]]:
        """Get an existing App Runner service for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The App Runner service dictionary, or None if it doesn't exist.

        Raises:
            ClientError: If the App Runner service cannot be described.
        """
        existing_metadata = AppRunnerDeploymentMetadata.from_deployment(
            deployment
        )

        if not existing_metadata.service_arn:
            return None

        try:
            response = self.app_runner_client.describe_service(
                ServiceArn=existing_metadata.service_arn
            )
            return response["Service"]  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            raise

    def _get_service_operational_state(
        self,
        service: Dict[str, Any],
        region: str,
        secret_arn: Optional[str] = None,
    ) -> DeploymentOperationalState:
        """Get the operational state of an App Runner service.

        Args:
            service: The App Runner service dictionary.
            region: The AWS region.
            secret_arn: The active Secrets Manager secret ARN.

        Returns:
            The operational state of the App Runner service.
        """
        metadata = AppRunnerDeploymentMetadata.from_app_runner_service(
            service, region, secret_arn
        )

        state = DeploymentOperationalState(
            status=DeploymentStatus.UNKNOWN,
            metadata=metadata.model_dump(exclude_none=True),
        )

        # Map App Runner service status to ZenML status. Valid values are:
        # - CREATE_FAILED
        # - DELETE_FAILED
        # - RUNNING
        # - DELETED
        # - PAUSED
        # - OPERATION_IN_PROGRESS
        service_status = service.get("Status", "").upper()

        if service_status in [
            "CREATE_FAILED",
            "DELETE_FAILED",
        ]:
            state.status = DeploymentStatus.ERROR
        elif service_status == "OPERATION_IN_PROGRESS":
            state.status = DeploymentStatus.PENDING
        elif service_status == "RUNNING":
            state.status = DeploymentStatus.RUNNING
            state.url = service.get("ServiceUrl")
            if state.url and not state.url.startswith("https://"):
                state.url = f"https://{state.url}"
        elif service_status == "DELETED":
            state.status = DeploymentStatus.ABSENT
        elif service_status == "PAUSED":
            state.status = (
                DeploymentStatus.PENDING
            )  # Treat paused as pending for now
        else:
            state.status = DeploymentStatus.UNKNOWN

        return state

    def _requires_service_replacement(
        self,
        existing_service: Dict[str, Any],
        settings: AWSDeployerSettings,
    ) -> bool:
        """Check if the service configuration requires replacement.

        App Runner only requires service replacement for fundamental service-level
        changes that cannot be handled through revisions:

        - Network access configuration
        - VPC configuration
        - Encryption configuration
        - Observability configuration

        All other configuration changes (image, resources, environment, scaling)
        can be handled as updates.

        Args:
            existing_service: The existing App Runner service.
            settings: The new deployer settings.

        Returns:
            True if the service needs to be replaced, False if it can be updated.
        """
        network_config = existing_service.get("NetworkConfiguration", {})
        ingress_config = network_config.get("IngressConfiguration", {})
        current_public_access = ingress_config.get("IsPubliclyAccessible")
        if current_public_access != settings.is_publicly_accessible:
            return True

        current_vpc_config = network_config.get("EgressConfiguration", {})
        has_current_vpc = bool(current_vpc_config.get("VpcConnectorArn"))
        will_have_vpc = bool(settings.ingress_vpc_configuration)
        if has_current_vpc != will_have_vpc:
            return True

        current_encryption = existing_service.get(
            "EncryptionConfiguration", {}
        )
        current_kms_key = current_encryption.get("KmsKey")
        if current_kms_key != settings.encryption_kms_key:
            return True

        return False

    def _convert_resource_settings_to_aws_format(
        self,
        resource_settings: ResourceSettings,
        resource_combinations: List[Tuple[float, float]],
        strict_resource_matching: bool = False,
    ) -> Tuple[str, str]:
        """Convert ResourceSettings to AWS App Runner resource format.

        AWS App Runner only supports specific CPU-memory combinations.
        This method selects the best combination that meets the requirements.

        Args:
            resource_settings: The resource settings from pipeline configuration.
            resource_combinations: List of supported CPU (vCPU) and memory (GB)
                combinations.
            strict_resource_matching: Whether to enforce strict matching of
                resource requirements to AWS App Runner supported CPU and
                memory combinations or approximate the closest matching
                supported combination.

        Returns:
            Tuple of (cpu, memory) in AWS App Runner format.
        """
        requested_cpu = resource_settings.cpu_count
        requested_memory_gb = None
        if resource_settings.memory is not None:
            requested_memory_gb = resource_settings.get_memory(unit="GB")

        cpu, memory = self._select_aws_cpu_memory_combination(
            requested_cpu,
            requested_memory_gb,
            resource_combinations,
            strict_resource_matching,
        )

        return cpu, memory

    def _select_aws_cpu_memory_combination(
        self,
        requested_cpu: Optional[float],
        requested_memory_gb: Optional[float],
        resource_combinations: List[Tuple[float, float]],
        strict_resource_matching: bool = False,
    ) -> Tuple[str, str]:
        """Select the best AWS App Runner CPU-memory combination.

        AWS App Runner only supports specific CPU and memory combinations, e.g.:
        - 0.25 vCPU: 0.5 GB, 1 GB
        - 0.5 vCPU: 1 GB
        - 1 vCPU: 2 GB, 3 GB, 4 GB
        - 2 vCPU: 4 GB, 6 GB
        - 4 vCPU: 8 GB, 10 GB, 12 GB

        This method selects the best combination that meets the requirements.

        Args:
            requested_cpu: Requested CPU count (can be None)
            requested_memory_gb: Requested memory in GB (can be None)
            resource_combinations: List of supported CPU (vCPU) and memory (GB)
                combinations.
            strict_resource_matching: Whether to enforce strict matching of
                resource requirements to AWS App Runner supported CPU and
                memory combinations or approximate the closest matching
                supported combination.

        Returns:
            Tuple of (cpu, memory) that best matches requirements, in AWS App
            Runner format.

        Raises:
            ValueError: If the requested resource requirements cannot be matched
                to any of the supported combinations for the AWS App Runner
                service and strict_resource_matching is True.
        """
        if requested_cpu is None and requested_memory_gb is None:
            return f"{DEFAULT_CPU:g} vCPU", f"{DEFAULT_MEMORY:g} GB"

        sorted_combinations = sorted(resource_combinations)

        best_combination = None
        exact_match = False
        best_score = float("inf")  # Lower is better

        for cpu_val, mem_val in sorted_combinations:
            cpu_ok = requested_cpu is None or cpu_val >= requested_cpu
            mem_ok = (
                requested_memory_gb is None or mem_val >= requested_memory_gb
            )
            exact_match = (
                cpu_val == requested_cpu and mem_val == requested_memory_gb
            )
            if exact_match:
                best_combination = (cpu_val, mem_val)
                break

            if cpu_ok and mem_ok:
                # Calculate "waste" score (how much over-provisioning)
                cpu_waste = (
                    0 if requested_cpu is None else (cpu_val - requested_cpu)
                )
                mem_waste = (
                    0
                    if requested_memory_gb is None
                    else (mem_val - requested_memory_gb)
                )

                # Prioritize CPU requirements, then memory
                score = cpu_waste * 10 + mem_waste

                if score < best_score:
                    best_score = score
                    best_combination = (cpu_val, mem_val)

        # If no combination satisfies requirements, use the highest available
        if best_combination is None:
            best_combination = sorted_combinations[-1]

        result = (
            f"{best_combination[0]:g} vCPU",
            f"{best_combination[1]:g} GB",
        )

        if strict_resource_matching and not exact_match:
            raise ValueError(
                f"Requested resource requirements ({requested_cpu} vCPU, "
                f"{requested_memory_gb} GB) cannot be matched to any of the "
                f"supported combinations for the AWS App Runner service. "
                f"The closest matching combination is {result[0]} and "
                f"{result[1]}."
            )

        return result

    def _convert_scaling_settings_to_aws_format(
        self,
        resource_settings: ResourceSettings,
    ) -> Tuple[int, int, int]:
        """Convert ResourceSettings scaling to AWS App Runner format.

        Args:
            resource_settings: The resource settings from pipeline configuration.

        Returns:
            Tuple of (min_replicas, max_replicas, max_concurrency) for AWS App
            Runner.
        """
        min_replicas = DEFAULT_MIN_REPLICAS
        if resource_settings.min_replicas is not None:
            min_replicas = max(
                1, resource_settings.min_replicas
            )  # AWS App Runner min is 1

        max_replicas = DEFAULT_MAX_REPLICAS
        if resource_settings.max_replicas is not None:
            # ResourceSettings uses 0 to mean "no limit"
            # AWS App Runner needs a specific value, so we use the platform maximum
            if resource_settings.max_replicas == 0:
                max_replicas = AWS_APP_RUNNER_MAX_SIZE
            else:
                max_replicas = min(
                    resource_settings.max_replicas, AWS_APP_RUNNER_MAX_SIZE
                )

        max_concurrency = DEFAULT_MAX_CONCURRENCY
        if resource_settings.max_concurrency is not None:
            max_concurrency = min(
                resource_settings.max_concurrency,
                AWS_APP_RUNNER_MAX_CONCURRENCY,
            )

        return min_replicas, max_replicas, max_concurrency

    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Serve a pipeline as an App Runner service.

        Args:
            deployment: The deployment to serve.
            stack: The stack the pipeline will be deployed on.
            environment: Environment variables to set.
            secrets: Secret environment variables to set.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be provisioned.

        Returns:
            The operational state of the provisioned deployment.

        Raises:
            DeploymentProvisionError: If the deployment fails.
            DeploymentDeprovisionError: If the previous deployment fails to
                deprovision.
            DeployerError: If an unexpected error occurs.
        """
        snapshot = deployment.snapshot
        assert snapshot, "Pipeline snapshot not found"

        settings = cast(
            AWSDeployerSettings,
            self.get_settings(snapshot),
        )

        resource_settings = snapshot.pipeline_configuration.resource_settings

        cpu, memory = self._convert_resource_settings_to_aws_format(
            resource_settings,
            self.config.resource_combinations,
            settings.strict_resource_matching,
        )
        min_size, max_size, max_concurrency = (
            self._convert_scaling_settings_to_aws_format(
                resource_settings,
            )
        )

        client = self.app_runner_client

        service_name = self._get_service_name(
            deployment.name, deployment.id, settings.service_name_prefix
        )

        existing_service = self._get_app_runner_service(deployment)
        image = self.get_image(snapshot)
        region = self.region

        if existing_service and self._requires_service_replacement(
            existing_service, settings
        ):
            try:
                self.do_deprovision_deployment(deployment, timeout)
            except DeploymentNotFoundError:
                logger.warning(
                    f"Deployment '{deployment.name}' not found, "
                    f"skipping deprovision of existing App Runner service"
                )
            except DeployerError as e:
                raise DeploymentDeprovisionError(
                    f"Failed to deprovision existing App Runner service for "
                    f"deployment '{deployment.name}': {e}\n"
                    "Bailing out to avoid leaving orphaned resources."
                    "You might need to manually delete the existing App Runner "
                    "service instance to continue or forcefully delete the "
                    "deployment."
                )
            existing_service = None

        entrypoint = DeploymentEntrypointConfiguration.get_entrypoint_command()
        arguments = DeploymentEntrypointConfiguration.get_entrypoint_arguments(
            **{
                DEPLOYMENT_ID_OPTION: deployment.id,
            }
        )

        env_vars, secret_refs, active_secret_arn = (
            self._prepare_environment_variables(
                deployment, environment, secrets, settings
            )
        )

        # AWS App Runner only supports ECR repositories.
        if "public.ecr.aws" in image:
            image_repo_type = "ECR_PUBLIC"
        elif "amazonaws.com" in image:
            image_repo_type = "ECR"
        else:
            raise DeploymentProvisionError(
                f"AWS App Runner only supports Amazon ECR and ECR Public "
                f"repositories. The container image '{image}' does not appear "
                f"to be hosted on either platform. Supported image repositories:\n"
                f"- ECR Public: public.ecr.aws/...\n"
                f"- ECR Private: *.amazonaws.com/...\n"
                f"Please push your image to one of these registries before "
                f"deploying to App Runner."
            )

        container_port = (
            snapshot.pipeline_configuration.deployment_settings.uvicorn_port
        )
        image_config: Dict[str, Any] = {
            "Port": str(container_port),
            "StartCommand": " ".join(entrypoint + arguments),
        }

        if env_vars:
            image_config["RuntimeEnvironmentVariables"] = env_vars

        if secret_refs:
            image_config["RuntimeEnvironmentSecrets"] = secret_refs

        image_repository_config = {
            "ImageIdentifier": image,
            "ImageConfiguration": image_config,
            "ImageRepositoryType": image_repo_type,
        }

        source_configuration = {
            "ImageRepository": image_repository_config,
            # We don't want to automatically deploy new revisions when new
            # container images are pushed to the repository.
            "AutoDeploymentsEnabled": False,
        }

        if settings.access_role_arn:
            source_configuration["AuthenticationConfiguration"] = {
                "AccessRoleArn": settings.access_role_arn
            }
        elif image_repo_type == "ECR":
            logger.warning(
                "Using private ECR repository without explicit access_role_arn. "
                "Ensure the default App Runner service role has permissions to "
                f"pull the '{image}' image from the repository, or specify "
                "access_role_arn in deployer settings."
            )

        instance_configuration = {
            "Cpu": cpu,
            "Memory": memory,
        }
        if settings.instance_role_arn:
            instance_configuration["InstanceRoleArn"] = (
                settings.instance_role_arn
            )
        elif secret_refs:
            logger.warning(
                "Storing secrets in AWS Secrets Manager is enabled but no "
                "explicit instance role is provided. Ensure the default "
                "App Runner service role has secretsmanager:GetSecretValue "
                "permissions, provide an explicit instance role or disable "
                "'use_secrets_manager' in deployer settings."
            )

        auto_scaling_config_name = self._get_auto_scaling_config_name(
            deployment.name, deployment.id
        )
        auto_scaling_config_arn = self._create_or_update_auto_scaling_config(
            auto_scaling_config_name,
            min_size,
            max_size,
            max_concurrency,
            deployment,
            settings,
        )

        health_check_configuration = {
            "Protocol": settings.health_check_protocol,
            "Interval": settings.health_check_interval_seconds,
            "Timeout": settings.health_check_timeout_seconds,
            "HealthyThreshold": settings.health_check_healthy_threshold,
            "UnhealthyThreshold": settings.health_check_unhealthy_threshold,
        }

        deployment_settings = (
            snapshot.pipeline_configuration.deployment_settings
        )

        if settings.health_check_protocol.upper() == "HTTP":
            root_path = deployment_settings.root_url_path
            api_url_path = deployment_settings.api_url_path
            health_check_path = f"{root_path}{api_url_path}{deployment_settings.health_url_path}"
            health_check_configuration["Path"] = health_check_path

        network_configuration = {
            "IngressConfiguration": {
                "IsPubliclyAccessible": settings.is_publicly_accessible,
            }
        }

        traffic_configurations = []
        for revision, percent in settings.traffic_allocation.items():
            if revision == "LATEST":
                traffic_configurations.append(
                    {
                        "Type": "LATEST",
                        "Percent": percent,
                    }
                )
            else:
                if revision.startswith("tag:"):
                    traffic_configurations.append(
                        {
                            "Tag": revision[4:],  # Remove "tag:" prefix
                            "Percent": percent,
                        }
                    )
                else:
                    traffic_configurations.append(
                        {
                            "Revision": revision,
                            "Percent": percent,
                        }
                    )

        if settings.ingress_vpc_configuration:
            vpc_config = json.loads(settings.ingress_vpc_configuration)
            network_configuration["IngressConfiguration"][
                "VpcIngressConnectionConfiguration"
            ] = vpc_config

        encryption_configuration = None
        if settings.encryption_kms_key:
            encryption_configuration = {
                "KmsKey": settings.encryption_kms_key,
            }

        observability_configuration = None
        if settings.observability_configuration_arn:
            observability_configuration = {
                "ObservabilityEnabled": True,
                "ObservabilityConfigurationArn": settings.observability_configuration_arn,
            }

        service_tags = self.get_tags(deployment, settings)

        try:
            if existing_service:
                logger.debug(
                    f"Updating existing App Runner service for pipeline "
                    f"deployment '{deployment.name}'"
                )

                update_request = {
                    "ServiceArn": existing_service["ServiceArn"],
                    "SourceConfiguration": source_configuration,
                    "InstanceConfiguration": instance_configuration,
                    "AutoScalingConfigurationArn": auto_scaling_config_arn,
                    "HealthCheckConfiguration": health_check_configuration,
                    "NetworkConfiguration": network_configuration,
                }

                if not (
                    len(traffic_configurations) == 1
                    and traffic_configurations[0].get("Type") == "LATEST"
                    and traffic_configurations[0].get("Percent") == 100
                ):
                    update_request["TrafficConfiguration"] = (
                        traffic_configurations
                    )

                if encryption_configuration:
                    update_request["EncryptionConfiguration"] = (
                        encryption_configuration
                    )

                if observability_configuration:
                    update_request["ObservabilityConfiguration"] = (
                        observability_configuration
                    )

                response = client.update_service(**update_request)
                service_arn = response["Service"]["ServiceArn"]

                # Update tags separately
                client.tag_resource(
                    ResourceArn=service_arn,
                    Tags=service_tags,
                )

                updated_service = response["Service"]
            else:
                logger.debug(
                    f"Creating new App Runner service for deployment "
                    f"'{deployment.name}' in region {region}"
                )

                create_request = {
                    "ServiceName": service_name,
                    "SourceConfiguration": source_configuration,
                    "InstanceConfiguration": instance_configuration,
                    "AutoScalingConfigurationArn": auto_scaling_config_arn,
                    "Tags": service_tags,
                    "HealthCheckConfiguration": health_check_configuration,
                    "NetworkConfiguration": network_configuration,
                }

                if encryption_configuration:
                    create_request["EncryptionConfiguration"] = (
                        encryption_configuration
                    )

                if observability_configuration:
                    create_request["ObservabilityConfiguration"] = (
                        observability_configuration
                    )

                # Only add traffic configuration if it's not the default
                # (100% LATEST)
                if not (
                    len(traffic_configurations) == 1
                    and traffic_configurations[0].get("Type") == "LATEST"
                    and traffic_configurations[0].get("Percent") == 100
                ):
                    create_request["TrafficConfiguration"] = (
                        traffic_configurations
                    )

                response = client.create_service(**create_request)
                updated_service = response["Service"]

            return self._get_service_operational_state(
                updated_service, region, active_secret_arn
            )

        except (ClientError, BotoCoreError) as e:
            raise DeploymentProvisionError(
                f"Failed to deploy App Runner service for deployment "
                f"'{deployment.name}': {e}"
            )
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while provisioning deployment "
                f"'{deployment.name}': {e}"
            )

    def do_get_deployment_state(
        self,
        deployment: DeploymentResponse,
    ) -> DeploymentOperationalState:
        """Get information about an App Runner deployment.

        Args:
            deployment: The deployment to get information about.

        Returns:
            The operational state of the deployment.

        Raises:
            DeploymentNotFoundError: If the deployment is not found.
            RuntimeError: If the service ARN is not found in the deployment metadata.
        """
        service = self._get_app_runner_service(deployment)

        if service is None:
            raise DeploymentNotFoundError(
                f"App Runner service for deployment '{deployment.name}' "
                "not found"
            )

        existing_metadata = AppRunnerDeploymentMetadata.from_deployment(
            deployment
        )

        if not existing_metadata.region:
            raise RuntimeError(
                f"Region not found in deployment metadata for "
                f"deployment '{deployment.name}'"
            )

        existing_secret_arn = self._get_secret_arn(deployment)

        return self._get_service_operational_state(
            service,
            existing_metadata.region,
            existing_secret_arn,
        )

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of an App Runner deployment.

        Args:
            deployment: The deployment to get the logs of.
            follow: If True, stream logs as they are written.
            tail: Only retrieve the last NUM lines of log output.

        Yields:
            The logs of the deployment.

        Raises:
            NotImplementedError: If log following is requested.
            DeploymentNotFoundError: If the deployment is not found.
            DeploymentLogsNotFoundError: If the logs are not found.
            DeployerError: If an unexpected error occurs.
            RuntimeError: If the service name is not found in the deployment metadata.
        """
        if follow:
            raise NotImplementedError(
                "Log following is not yet implemented for App Runner deployer"
            )

        service = self._get_app_runner_service(deployment)
        if service is None:
            raise DeploymentNotFoundError(
                f"App Runner service for deployment '{deployment.name}' not "
                "found"
            )

        try:
            existing_metadata = AppRunnerDeploymentMetadata.from_deployment(
                deployment
            )
            service_name = existing_metadata.service_name
            service_id = existing_metadata.service_id
            if not service_name or not service_id:
                raise RuntimeError(
                    f"Service name or ID not found in deployment metadata for "
                    f"deployment '{deployment.name}'"
                )

            # App Runner automatically creates CloudWatch log groups
            log_group_name = (
                f"/aws/apprunner/{service_name}/{service_id}/application"
            )

            try:
                streams_response = self.logs_client.describe_log_streams(
                    logGroupName=log_group_name,
                    orderBy="LastEventTime",
                    descending=True,
                )

                log_lines = []
                for stream in streams_response.get("logStreams", []):
                    stream_name = stream["logStreamName"]

                    events_response = self.logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=stream_name,
                        startFromHead=False,  # Get most recent first
                    )

                    for event in events_response.get("events", []):
                        timestamp = event.get("timestamp", 0)
                        message = event.get("message", "")

                        dt = datetime.datetime.fromtimestamp(
                            timestamp / 1000.0
                        )
                        formatted_time = dt.isoformat()

                        log_line = f"[{formatted_time}] {message}"
                        log_lines.append(log_line)

                # Sort by timestamp (most recent last for tail to work correctly)
                log_lines.sort()

                if tail is not None and tail > 0:
                    log_lines = log_lines[-tail:]

                for log_line in log_lines:
                    yield log_line

            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    raise DeploymentLogsNotFoundError(
                        f"Log group not found for App Runner service "
                        f"'{service_name}'"
                    )
                raise

        except (ClientError, BotoCoreError) as e:
            raise DeploymentLogsNotFoundError(
                f"Failed to retrieve logs for deployment '{deployment.name}': "
                f"{e}"
            )
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while retrieving logs for deployment "
                f"'{deployment.name}': {e}"
            )

    def do_deprovision_deployment(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision an App Runner deployment.

        Args:
            deployment: The deployment to deprovision.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be deprovisioned.

        Returns:
            The operational state of the deprovisioned deployment, or None if
            deletion is completed immediately.

        Raises:
            DeploymentNotFoundError: If the deployment is not found.
            DeploymentDeprovisionError: If the deprovision fails.
            DeployerError: If an unexpected error occurs.
            RuntimeError: If the service ARN is not found in the deployment metadata.
        """
        service = self._get_app_runner_service(deployment)
        if service is None:
            raise DeploymentNotFoundError(
                f"App Runner service for deployment '{deployment.name}' not "
                "found"
            )

        try:
            existing_metadata = AppRunnerDeploymentMetadata.from_deployment(
                deployment
            )
            if not existing_metadata.service_arn:
                raise RuntimeError(
                    f"Service ARN not found in deployment metadata for "
                    f"deployment '{deployment.name}'"
                )

            logger.debug(
                f"Deleting App Runner service for deployment "
                f"'{deployment.name}'"
            )

            # Delete the service
            self.app_runner_client.delete_service(
                ServiceArn=existing_metadata.service_arn
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise DeploymentNotFoundError(
                    f"App Runner service for deployment '{deployment.name}' "
                    "not found"
                )
            raise DeploymentDeprovisionError(
                f"Failed to delete App Runner service for deployment "
                f"'{deployment.name}': {e}"
            )
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while deleting deployment "
                f"'{deployment.name}': {e}"
            )

        deployment_before_deletion = deployment

        # App Runner deletion is asynchronous and the auto-scaling configuration
        # and secrets need to be cleaned up after the service is deleted. So we
        # poll the service here instead of doing it in the base deployer class.
        deployment, deployment_state = self._poll_deployment(
            deployment, DeploymentStatus.ABSENT, timeout
        )

        if deployment_state.status != DeploymentStatus.ABSENT:
            return deployment_state

        try:
            self._cleanup_deployment_secrets(deployment_before_deletion)

            self._cleanup_deployment_auto_scaling_config(
                deployment_before_deletion
            )
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while cleaning up resources for pipeline "
                f"deployment '{deployment.name}': {e}"
            )

        return None
