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
"""Implementation of the GCP Cloud Run deployer."""

import math
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

from google.api_core import exceptions as google_exceptions
from google.cloud import run_v2, secretmanager
from google.cloud.logging_v2 import Client as LoggingClient
from google.protobuf.json_format import MessageToDict
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
from zenml.integrations.gcp.flavors.gcp_deployer_flavor import (
    GCPDeployerConfig,
    GCPDeployerSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
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
DEFAULT_CPU = "1"
DEFAULT_MEMORY = "2Gi"
DEFAULT_MIN_INSTANCES = 1
DEFAULT_MAX_INSTANCES = 100
DEFAULT_CONCURRENCY = 80

# GCP Cloud Run built-in limits
GCP_CLOUD_RUN_MAX_INSTANCES = 1000


class CloudRunDeploymentMetadata(BaseModel):
    """Metadata for a Cloud Run deployment."""

    service_name: Optional[str] = None
    service_url: Optional[str] = None
    project_id: Optional[str] = None
    location: Optional[str] = None
    revision_name: Optional[str] = None
    reconciling: Optional[bool] = None
    service_status: Optional[Dict[str, Any]] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None
    min_instances: Optional[int] = None
    max_instances: Optional[int] = None
    concurrency: Optional[int] = None
    timeout_seconds: Optional[int] = None
    ingress: Optional[str] = None
    vpc_connector: Optional[str] = None
    service_account: Optional[str] = None
    execution_environment: Optional[str] = None
    port: Optional[int] = None
    allow_unauthenticated: Optional[bool] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None
    traffic_allocation: Optional[Dict[str, int]] = None
    created_time: Optional[str] = None
    updated_time: Optional[str] = None
    secrets: List[str] = []

    @classmethod
    def from_cloud_run_service(
        cls,
        service: run_v2.Service,
        project_id: str,
        location: str,
        secrets: List[secretmanager.Secret],
    ) -> "CloudRunDeploymentMetadata":
        """Create metadata from a Cloud Run service.

        Args:
            service: The Cloud Run service object.
            project_id: The GCP project ID.
            location: The GCP location.
            secrets: The list of existing GCP Secret Manager secrets for the
                deployment.

        Returns:
            The metadata for the Cloud Run service.
        """
        container = None
        if service.template and service.template.containers:
            container = service.template.containers[0]

        cpu = None
        memory = None
        if container and container.resources and container.resources.limits:
            cpu = container.resources.limits.get("cpu")
            memory = container.resources.limits.get("memory")

        min_instances = None
        max_instances = None
        if service.template and service.template.scaling:
            scaling = service.template.scaling
            min_instances = scaling.min_instance_count
            max_instances = scaling.max_instance_count

        concurrency = None
        if service.template:
            concurrency = service.template.max_instance_request_concurrency

        timeout_seconds = None
        if service.template and service.template.timeout:
            timeout_seconds = service.template.timeout.seconds

        ingress = None
        if service.ingress:
            ingress = str(service.ingress)

        vpc_connector = None
        if service.template and service.template.vpc_access:
            vpc_connector = service.template.vpc_access.connector

        service_account = None
        if service.template:
            service_account = service.template.service_account

        execution_environment = None
        if service.template and service.template.execution_environment:
            execution_environment = str(service.template.execution_environment)

        port = None
        if container and container.ports:
            port = container.ports[0].container_port

        traffic_allocation = {}
        if service.traffic:
            for traffic in service.traffic:
                if traffic.revision:
                    traffic_allocation[traffic.revision] = traffic.percent
                elif traffic.tag:
                    traffic_allocation[traffic.tag] = traffic.percent
                else:
                    traffic_allocation["LATEST"] = traffic.percent

        return cls(
            service_name=service.name.split("/")[-1] if service.name else None,
            service_url=service.uri if hasattr(service, "uri") else None,
            project_id=project_id,
            location=location,
            revision_name=(
                service.template.revision
                if service.template and service.template.revision
                else None
            ),
            reconciling=service.reconciling,
            service_status=MessageToDict(
                service.terminal_condition._pb,
            )
            if service.terminal_condition
            else None,
            cpu=cpu,
            memory=memory,
            min_instances=min_instances,
            max_instances=max_instances,
            concurrency=concurrency,
            timeout_seconds=timeout_seconds,
            ingress=ingress,
            vpc_connector=vpc_connector,
            service_account=service_account,
            execution_environment=execution_environment,
            port=port,
            allow_unauthenticated=True,
            labels=dict(service.labels) if service.labels else {},
            annotations=dict(service.annotations)
            if service.annotations
            else {},
            traffic_allocation=traffic_allocation,
            created_time=(
                service.create_time.isoformat()
                if service.create_time
                else None
            ),
            updated_time=(
                service.update_time.isoformat()
                if service.update_time
                else None
            ),
            secrets=[secret.name for secret in secrets],
        )

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "CloudRunDeploymentMetadata":
        """Create metadata from a deployment.

        Args:
            deployment: The deployment to get the metadata for.

        Returns:
            The metadata for the deployment.
        """
        return cls.model_validate(deployment.deployment_metadata)


class GCPDeployer(ContainerizedDeployer, GoogleCredentialsMixin):
    """Deployer responsible for deploying pipelines on GCP Cloud Run."""

    _credentials: Optional[Any] = None
    _project_id: Optional[str] = None
    _cloud_run_client: Optional[run_v2.ServicesClient] = None
    _logging_client: Optional[LoggingClient] = None
    _secret_manager_client: Optional[
        secretmanager.SecretManagerServiceClient
    ] = None

    @property
    def config(self) -> GCPDeployerConfig:
        """Returns the `GCPDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(GCPDeployerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the GCP deployer.

        Returns:
            The settings class.
        """
        return GCPDeployerSettings

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

    def _get_credentials_and_project_id(self) -> Tuple[Any, str]:
        """Get GCP credentials and project ID.

        Returns:
            A tuple containing the credentials and project ID.
        """
        if (
            self._credentials is not None
            and self._project_id is not None
            and not self.connector_has_expired()
        ):
            return self._credentials, self._project_id

        credentials, project_id = self._get_authentication()

        self._credentials = credentials
        self._project_id = project_id
        return credentials, project_id

    @property
    def project_id(self) -> str:
        """Get the GCP project ID.

        Returns:
            The GCP project ID.
        """
        _, project_id = self._get_credentials_and_project_id()
        return project_id

    @property
    def cloud_run_client(self) -> run_v2.ServicesClient:
        """Get the Cloud Run client.

        Returns:
            The Cloud Run client.
        """
        if self._cloud_run_client is None or self.connector_has_expired():
            credentials, _ = self._get_credentials_and_project_id()
            self._cloud_run_client = run_v2.ServicesClient(
                credentials=credentials
            )
        return self._cloud_run_client

    @property
    def logging_client(self) -> LoggingClient:
        """Get the Cloud Logging client.

        Returns:
            The Cloud Logging client.
        """
        if self._logging_client is None or self.connector_has_expired():
            credentials, project_id = self._get_credentials_and_project_id()
            self._logging_client = LoggingClient(
                project=project_id, credentials=credentials
            )
        return self._logging_client

    @property
    def secret_manager_client(
        self,
    ) -> secretmanager.SecretManagerServiceClient:
        """Get the Secret Manager client.

        Returns:
            The Secret Manager client.
        """
        if self._secret_manager_client is None or self.connector_has_expired():
            credentials, _ = self._get_credentials_and_project_id()
            self._secret_manager_client = (
                secretmanager.SecretManagerServiceClient(
                    credentials=credentials
                )
            )
        return self._secret_manager_client

    def get_labels(
        self, deployment: DeploymentResponse, settings: GCPDeployerSettings
    ) -> Dict[str, str]:
        """Get the labels for a deployment.

        Args:
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            The labels for the deployment.
        """
        return {
            **settings.labels,
            "zenml-deployment-id": str(deployment.id),
            "zenml-deployment-name": deployment.name,
            "zenml-deployer-name": str(self.name),
            "zenml-deployer-id": str(self.id),
            "managed-by": "zenml",
        }

    def _sanitize_name(
        self,
        name: str,
        random_suffix: str,
        max_length: int = 63,
    ) -> str:
        """Sanitize a name to comply with GCP naming requirements.

        Common GCP naming requirements:
        - Length: 1-max_length characters
        - Characters: lowercase letters (a-z), numbers (0-9), hyphens (-)
        - Must start and end with a letter or number

        Args:
            name: The raw name to sanitize.
            random_suffix: A random suffix to add to the name to ensure
                uniqueness.
            max_length: The maximum length of the name.

        Returns:
            A sanitized name that complies with GCP requirements.

        Raises:
            RuntimeError: If the random suffix is invalid.
            ValueError: If the service name is invalid.
        """
        if (
            not re.match(r"^[a-z0-9]+$", random_suffix)
            or len(random_suffix) < 1
        ):
            raise RuntimeError(
                f"Invalid random suffix: {random_suffix}. Must contain only "
                "lowercase letters and numbers and be at least 1 character "
                "long."
            )

        # Convert to lowercase and replace all disallowed characters with
        # hyphens
        sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())

        # Remove consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)

        # Remove leading and trailing hyphens before truncating
        sanitized = re.sub(
            r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$",
            "",
            sanitized,
        )

        # Truncate to fit within max_length character limit including suffix
        max_base_length = (
            max_length - len(random_suffix) - 1  # -1 for the hyphen
        )
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

        return f"{sanitized}-{random_suffix}"

    def _get_service_name(
        self, deployment_name: str, deployment_id: UUID, prefix: str
    ) -> str:
        """Get the Cloud Run service name for a deployment.

        Args:
            deployment_id: The deployment ID.
            deployment_name: The deployment name.
            prefix: The prefix to use for the service name.

        Returns:
            The Cloud Run service name that complies with all naming requirements.
        """
        deployment_id_short = str(deployment_id)[:8]
        raw_name = f"{prefix}{deployment_name}"

        return self._sanitize_name(
            raw_name, deployment_id_short, max_length=49
        )

    def _get_secret_name(
        self,
        deployment_id: UUID,
        env_var_name: str,
        prefix: str,
    ) -> str:
        """Get the Secret Manager secret name for an environment variable.

        Args:
            deployment_id: The deployment ID.
            env_var_name: The environment variable name.
            prefix: The prefix to use for the secret name.

        Returns:
            The Secret Manager secret name.
        """
        deployment_id_short = str(deployment_id)[:8]
        raw_name = f"{prefix}{env_var_name}"

        return self._sanitize_name(
            raw_name, deployment_id_short, max_length=255
        )

    def _create_or_update_secret(
        self,
        secret_name: str,
        secret_value: str,
        project_id: str,
        deployment: DeploymentResponse,
        settings: GCPDeployerSettings,
    ) -> secretmanager.Secret:
        """Create or update a secret in Secret Manager.

        Args:
            secret_name: The name of the secret.
            secret_value: The value to store.
            project_id: The GCP project ID.
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            The full secret.

        Raises:
            DeployerError: If secret creation/update fails.
        """
        parent = f"projects/{project_id}"
        secret_id = secret_name
        secret_path = f"{parent}/secrets/{secret_id}"

        try:
            try:
                secret = self.secret_manager_client.get_secret(
                    name=secret_path
                )
                logger.debug(
                    f"Secret {secret_name} already exists, adding new version"
                )
            except google_exceptions.NotFound:
                logger.debug(f"Creating new secret {secret_name}")
                secret = secretmanager.Secret(
                    replication=secretmanager.Replication(
                        automatic=secretmanager.Replication.Automatic()
                    ),
                    labels=self.get_labels(deployment, settings),
                )
                secret = self.secret_manager_client.create_secret(
                    parent=parent, secret_id=secret_id, secret=secret
                )

            payload = secretmanager.SecretPayload(
                data=secret_value.encode("utf-8")
            )
            version_response = self.secret_manager_client.add_secret_version(
                parent=secret_path, payload=payload
            )

            logger.debug(f"Created secret version: {version_response.name}")
            return secret

        except google_exceptions.GoogleAPICallError as e:
            raise DeployerError(
                f"Failed to create/update secret {secret_name}: {e}"
            )

    def _get_secrets(
        self, deployment: DeploymentResponse
    ) -> List[secretmanager.Secret]:
        """Get the existing GCP Secret Manager secrets for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The list of existing GCP Secret Manager secrets for the
            deployment.
        """
        metadata = CloudRunDeploymentMetadata.from_deployment(deployment)
        secrets: List[secretmanager.Secret] = []
        for secret_name in metadata.secrets:
            try:
                secret = self.secret_manager_client.get_secret(
                    name=secret_name
                )
                secrets.append(secret)
            except google_exceptions.NotFound:
                continue
            except google_exceptions.GoogleAPICallError:
                logger.exception(f"Failed to get secret {secret_name}")
                continue
        return secrets

    def _delete_secret(self, secret_name: str, project_id: str) -> None:
        """Delete a secret from Secret Manager.

        Args:
            secret_name: The name of the secret to delete.
            project_id: The GCP project ID.
        """
        secret_path = f"projects/{project_id}/secrets/{secret_name}"
        try:
            self.secret_manager_client.delete_secret(name=secret_path)
            logger.debug(f"Deleted secret {secret_path}")
        except google_exceptions.NotFound:
            logger.debug(f"Secret {secret_path} not found, skipping deletion")
        except google_exceptions.GoogleAPICallError:
            logger.exception(f"Failed to delete secret {secret_path}")

    def _cleanup_deployment_secrets(
        self,
        deployment: DeploymentResponse,
    ) -> None:
        """Clean up all secrets associated with a deployment.

        Args:
            deployment: The deployment.
        """
        secrets = self._get_secrets(deployment)

        for secret in secrets:
            _, project_id, _, secret_name = secret.name.split("/")
            self._delete_secret(secret_name, project_id)

    def _prepare_environment_variables(
        self,
        deployment: DeploymentResponse,
        environment: Dict[str, str],
        secrets: Dict[str, str],
        settings: GCPDeployerSettings,
        project_id: str,
    ) -> Tuple[List[run_v2.EnvVar], List[secretmanager.Secret]]:
        """Prepare environment variables for Cloud Run, handling secrets appropriately.

        Args:
            deployment: The deployment.
            environment: Regular environment variables.
            secrets: Sensitive environment variables.
            settings: The deployer settings.
            project_id: The GCP project ID.

        Returns:
            Tuple containing:
            - List of Cloud Run environment variable configurations.
            - List of active Secret Manager secrets.
        """
        env_vars = []

        merged_env = {**settings.environment_variables, **environment}
        for key, value in merged_env.items():
            env_vars.append(run_v2.EnvVar(name=key, value=value))

        active_secrets: List[secretmanager.Secret] = []
        if secrets:
            if settings.use_secret_manager:
                for key, value in secrets.items():
                    secret_name = self._get_secret_name(
                        deployment.id, key.lower(), settings.secret_name_prefix
                    )

                    try:
                        active_secret = self._create_or_update_secret(
                            secret_name,
                            value,
                            project_id,
                            deployment,
                            settings,
                        )

                        # Create environment variable that references the secret
                        env_var = run_v2.EnvVar(
                            name=key,
                            value_source=run_v2.EnvVarSource(
                                secret_key_ref=run_v2.SecretKeySelector(
                                    secret=secret_name, version="latest"
                                )
                            ),
                        )
                        env_vars.append(env_var)
                        active_secrets.append(active_secret)

                    except Exception as e:
                        logger.warning(
                            f"Failed to create secret for {key}, falling back "
                            f"to direct env var: {e}"
                        )
                        env_vars.append(run_v2.EnvVar(name=key, value=value))

                metadata = CloudRunDeploymentMetadata.from_deployment(
                    deployment
                )
                # Delete GCP secrets that are no longer needed
                active_secret_names = [
                    secret.name for secret in active_secrets
                ]
                for existing_secret_name in metadata.secrets:
                    if existing_secret_name not in active_secret_names:
                        _, project_id, _, secret_name = (
                            existing_secret_name.split("/")
                        )
                        self._delete_secret(secret_name, project_id)
            else:
                logger.warning(
                    "Storing secrets directly in environment variables. "
                    "Consider enabling use_secret_manager for better security."
                )
                for key, value in secrets.items():
                    env_vars.append(run_v2.EnvVar(name=key, value=value))

        return env_vars, active_secrets

    def _get_service_path(
        self,
        service_name: str,
        project_id: str,
        location: str,
    ) -> str:
        """Get the full Cloud Run service path.

        Args:
            service_name: The name of the Cloud Run service.
            project_id: The GCP project ID.
            location: The GCP location.

        Returns:
            The full Cloud Run service path.
        """
        return f"projects/{project_id}/locations/{location}/services/{service_name}"

    def _get_cloud_run_service(
        self, deployment: DeploymentResponse
    ) -> Optional[run_v2.Service]:
        """Get an existing Cloud Run service for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The Cloud Run service, or None if it doesn't exist.
        """
        existing_metadata = CloudRunDeploymentMetadata.from_deployment(
            deployment
        )

        if (
            not existing_metadata.service_name
            or not existing_metadata.location
            or not existing_metadata.project_id
        ):
            return None

        service_path = self._get_service_path(
            existing_metadata.service_name,
            existing_metadata.project_id,
            existing_metadata.location,
        )

        try:
            return self.cloud_run_client.get_service(name=service_path)
        except google_exceptions.NotFound:
            return None

    def _get_service_operational_state(
        self,
        service: run_v2.Service,
        project_id: str,
        location: str,
        secrets: List[secretmanager.Secret],
    ) -> DeploymentOperationalState:
        """Get the operational state of a Cloud Run service.

        Args:
            service: The Cloud Run service.
            project_id: The GCP project ID.
            location: The GCP location.
            secrets: The list of active Secret Manager secrets.

        Returns:
            The operational state of the Cloud Run service.
        """
        metadata = CloudRunDeploymentMetadata.from_cloud_run_service(
            service, project_id, location, secrets
        )

        state = DeploymentOperationalState(
            status=DeploymentStatus.UNKNOWN,
            metadata=metadata.model_dump(exclude_none=True),
        )

        # This flag is set while the service is being reconciled
        if service.reconciling:
            state.status = DeploymentStatus.PENDING
        else:
            if (
                service.terminal_condition.state
                == run_v2.Condition.State.CONDITION_SUCCEEDED
            ):
                state.status = DeploymentStatus.RUNNING
                state.url = service.uri
            elif (
                service.terminal_condition.state
                == run_v2.Condition.State.CONDITION_FAILED
            ):
                state.status = DeploymentStatus.ERROR
            elif service.terminal_condition.state in [
                run_v2.Condition.State.CONDITION_PENDING,
                run_v2.Condition.State.CONDITION_RECONCILING,
            ]:
                state.status = DeploymentStatus.PENDING
            else:
                state.status = DeploymentStatus.UNKNOWN

        return state

    def _convert_resource_settings_to_gcp_format(
        self,
        resource_settings: ResourceSettings,
    ) -> Tuple[str, str]:
        """Convert ResourceSettings to GCP Cloud Run resource format.

        GCP Cloud Run CPU constraints:
        - Fractional CPUs: 0.08 to < 1.0 (in increments of 0.01)
        - Integer CPUs: 1, 2, 4, 6, or 8 (no fractional values allowed >= 1.0)

        Args:
            resource_settings: The resource settings from pipeline configuration.

        Returns:
            Tuple of (cpu, memory) in GCP Cloud Run format.
        """
        cpu = DEFAULT_CPU
        if resource_settings.cpu_count is not None:
            cpu_count = resource_settings.cpu_count

            if cpu_count < 1.0:
                # For values < 1.0, allow fractional CPUs
                # Ensure minimum is 0.08 and round to 2 decimal places
                cpu_count = max(0.08, round(cpu_count, 2))
                cpu = str(cpu_count)
            else:
                # For values >= 1.0, round up to the nearest valid integer
                valid_cpu_values = [1, 2, 4, 6, 8]
                rounded_cpu = math.ceil(cpu_count)

                # Find the smallest valid CPU value that satisfies the requirement
                for valid_cpu in valid_cpu_values:
                    if valid_cpu >= rounded_cpu:
                        cpu = str(valid_cpu)
                        break
                else:
                    # If requested CPU exceeds maximum, use maximum
                    cpu = str(valid_cpu_values[-1])

        memory = DEFAULT_MEMORY
        memory_value_gib = None

        if resource_settings.memory is not None:
            memory_value_gib = resource_settings.get_memory(unit="GiB")

        final_memory_gib = self._validate_memory_for_cpu(cpu, memory_value_gib)

        if final_memory_gib is not None:
            if final_memory_gib == int(final_memory_gib):
                memory = f"{int(final_memory_gib)}Gi"
            else:
                memory = f"{final_memory_gib:.1f}Gi"

        return str(cpu), memory

    def _validate_memory_for_cpu(
        self, cpu: str, memory_gib: Optional[float]
    ) -> Optional[float]:
        """Validate and adjust memory allocation based on CPU requirements.

        GCP Cloud Run has minimum memory requirements per CPU configuration:
        - 1 CPU: 128 MiB minimum (0.125 GiB)
        - 2 CPU: 128 MiB minimum (0.125 GiB)
        - 4 CPU: 2 GiB minimum
        - 6 CPU: 4 GiB minimum
        - 8 CPU: 4 GiB minimum

        Args:
            cpu: CPU allocation as string (e.g., "1", "2", "4")
            memory_gib: Memory allocation in GiB (e.g., 2.0, 0.5, None)

        Returns:
            Adjusted memory allocation in GiB that meets minimum requirements, or None if no memory specified
        """
        if memory_gib is None:
            return None

        min_memory_per_cpu_gib = {
            1: 0.125,  # 128 MiB = 0.125 GiB
            2: 0.125,  # 128 MiB = 0.125 GiB
            4: 2.0,  # 2 GiB
            6: 4.0,  # 4 GiB
            8: 4.0,  # 4 GiB
        }

        # Handle fractional CPUs (< 1.0) - use minimum for 1 CPU
        cpu_float = float(cpu)
        if cpu_float < 1.0:
            cpu_int = 1
        else:
            cpu_int = int(cpu_float)

        required_memory_gib = min_memory_per_cpu_gib.get(cpu_int, 0.125)

        return max(memory_gib, required_memory_gib)

    def _convert_scaling_settings_to_gcp_format(
        self,
        resource_settings: ResourceSettings,
    ) -> Tuple[int, int]:
        """Convert ResourceSettings scaling to GCP Cloud Run format.

        Args:
            resource_settings: The resource settings from pipeline configuration.

        Returns:
            Tuple of (min_instances, max_instances) for GCP Cloud Run.
        """
        min_instances = DEFAULT_MIN_INSTANCES
        if resource_settings.min_replicas is not None:
            min_instances = resource_settings.min_replicas

        max_instances = DEFAULT_MAX_INSTANCES
        if resource_settings.max_replicas is not None:
            # ResourceSettings uses 0 to mean "no limit"
            # GCP Cloud Run needs a specific value, so we use the platform maximum
            if resource_settings.max_replicas == 0:
                max_instances = GCP_CLOUD_RUN_MAX_INSTANCES
            else:
                max_instances = resource_settings.max_replicas

        return min_instances, max_instances

    def _convert_concurrency_settings_to_gcp_format(
        self,
        resource_settings: ResourceSettings,
    ) -> int:
        """Convert ResourceSettings concurrency to GCP Cloud Run format.

        Args:
            resource_settings: The resource settings from pipeline configuration.

        Returns:
            The concurrency setting for GCP Cloud Run.
        """
        concurrency = DEFAULT_CONCURRENCY
        if resource_settings.max_concurrency is not None:
            concurrency = resource_settings.max_concurrency

        return concurrency

    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Serve a pipeline as a Cloud Run service.

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
            DeployerError: If an unexpected error occurs.
        """
        snapshot = deployment.snapshot
        assert snapshot, "Pipeline snapshot not found"

        settings = cast(
            GCPDeployerSettings,
            self.get_settings(snapshot),
        )

        resource_settings = snapshot.pipeline_configuration.resource_settings

        cpu, memory = self._convert_resource_settings_to_gcp_format(
            resource_settings,
        )
        min_instances, max_instances = (
            self._convert_scaling_settings_to_gcp_format(
                resource_settings,
            )
        )
        concurrency = self._convert_concurrency_settings_to_gcp_format(
            resource_settings,
        )

        project_id = self.project_id

        service_name = self._get_service_name(
            deployment.name, deployment.id, settings.service_name_prefix
        )

        service_path = self._get_service_path(
            service_name, project_id, settings.location
        )

        # If a previous deployment of the same deployment exists but with
        # a different service name, location, or project, we need to clean up
        # the old service.
        existing_metadata = CloudRunDeploymentMetadata.from_deployment(
            deployment
        )

        if (
            existing_metadata.service_name
            and existing_metadata.location
            and existing_metadata.project_id
        ):
            existing_service_path = self._get_service_path(
                existing_metadata.service_name,
                existing_metadata.project_id,
                existing_metadata.location,
            )
            if existing_service_path != service_path:
                try:
                    self.do_deprovision_deployment(deployment, timeout)
                except DeploymentNotFoundError:
                    logger.warning(
                        f"Deployment '{deployment.name}' not found, "
                        f"skipping deprovision of existing Cloud Run service"
                    )
                except DeployerError as e:
                    logger.warning(
                        f"Failed to deprovision existing Cloud Run service for "
                        f"deployment '{deployment.name}': {e}"
                    )

        image = self.get_image(snapshot)

        entrypoint = DeploymentEntrypointConfiguration.get_entrypoint_command()
        arguments = DeploymentEntrypointConfiguration.get_entrypoint_arguments(
            **{
                DEPLOYMENT_ID_OPTION: deployment.id,
            }
        )

        env_vars, active_secrets = self._prepare_environment_variables(
            deployment, environment, secrets, settings, project_id
        )

        resources = run_v2.ResourceRequirements(
            limits={
                "cpu": cpu,
                "memory": memory,
            }
        )

        scaling = run_v2.RevisionScaling(
            min_instance_count=min_instances,
            max_instance_count=max_instances,
        )

        vpc_access = None
        if settings.vpc_connector:
            vpc_access = run_v2.VpcAccess(connector=settings.vpc_connector)

        container_port = (
            snapshot.pipeline_configuration.deployment_settings.uvicorn_port
        )
        container = run_v2.Container(
            image=image,
            command=entrypoint,
            args=arguments,
            env=env_vars,
            resources=resources,
            ports=[run_v2.ContainerPort(container_port=container_port)],
        )

        template = run_v2.RevisionTemplate(
            labels=settings.labels,
            annotations=settings.annotations,
            scaling=scaling,
            vpc_access=vpc_access,
            max_instance_request_concurrency=concurrency,
            timeout=f"{settings.timeout_seconds}s",
            service_account=settings.service_account,
            containers=[container],
            execution_environment=(
                run_v2.ExecutionEnvironment.EXECUTION_ENVIRONMENT_GEN2
                if settings.execution_environment == "gen2"
                else run_v2.ExecutionEnvironment.EXECUTION_ENVIRONMENT_GEN1
            ),
        )

        traffic = []
        for revision, percent in settings.traffic_allocation.items():
            if revision == "LATEST":
                traffic.append(
                    run_v2.TrafficTarget(
                        type_=run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST,
                        percent=percent,
                    )
                )
            else:
                traffic.append(
                    run_v2.TrafficTarget(
                        revision=revision,
                        percent=percent,
                    )
                )

        ingress_mapping = {
            "all": run_v2.IngressTraffic.INGRESS_TRAFFIC_ALL,
            "internal": run_v2.IngressTraffic.INGRESS_TRAFFIC_INTERNAL_ONLY,
            "internal-and-cloud-load-balancing": run_v2.IngressTraffic.INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER,
        }
        ingress = ingress_mapping.get(
            settings.ingress, run_v2.IngressTraffic.INGRESS_TRAFFIC_ALL
        )

        # Create the service (name should NOT be set for CreateServiceRequest)
        service = run_v2.Service(
            labels=self.get_labels(deployment, settings),
            annotations=settings.annotations,
            template=template,
            traffic=traffic,
            ingress=ingress,
            invoker_iam_disabled=settings.allow_unauthenticated,
        )

        try:
            existing_service = None
            try:
                existing_service = self.cloud_run_client.get_service(
                    name=service_path
                )
            except google_exceptions.NotFound:
                pass

            if existing_service:
                # Update existing service - need to set the name in the
                # CreateServiceRequest for updates
                service.name = service_path
                logger.debug(
                    f"Updating existing Cloud Run service for pipeline "
                    f"deployment '{deployment.name}'"
                )
                self.cloud_run_client.update_service(service=service)
            else:
                logger.debug(
                    f"Creating new Cloud Run service for deployment "
                    f"'{deployment.name}'"
                )
                parent = f"projects/{project_id}/locations/{settings.location}"
                # Create new service - name must not be set in the
                # CreateServiceRequest, using service_id instead
                self.cloud_run_client.create_service(
                    parent=parent, service=service, service_id=service_name
                )
                # Adding the name here for the operational state retrieval
                service.name = service_path

            return self._get_service_operational_state(
                service, project_id, settings.location, active_secrets
            )

        except google_exceptions.GoogleAPICallError as e:
            raise DeploymentProvisionError(
                f"Failed to deploy Cloud Run service for deployment "
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
        """Get information about a Cloud Run deployment.

        Args:
            deployment: The deployment to get information about.

        Returns:
            The operational state of the deployment.

        Raises:
            DeploymentNotFoundError: If the deployment is not found.
            RuntimeError: If the project ID or location is not found in the
                deployment metadata.
        """
        service = self._get_cloud_run_service(deployment)

        if service is None:
            raise DeploymentNotFoundError(
                f"Cloud Run service for deployment '{deployment.name}' "
                "not found"
            )

        existing_metadata = CloudRunDeploymentMetadata.from_deployment(
            deployment
        )

        if not existing_metadata.project_id or not existing_metadata.location:
            raise RuntimeError(
                f"Project ID or location not found in deployment metadata for "
                f"deployment '{deployment.name}'"
            )

        existing_secrets = self._get_secrets(deployment)

        return self._get_service_operational_state(
            service,
            existing_metadata.project_id,
            existing_metadata.location,
            existing_secrets,
        )

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Cloud Run deployment.

        Args:
            deployment: The deployment to get the logs of.
            follow: If True, stream logs as they are written.
            tail: Only retrieve the last NUM lines of log output.

        Yields:
            The logs of the deployment.

        Raises:
            NotImplementedError: If log following is requested.
            DeploymentLogsNotFoundError: If the logs are not found.
            DeployerError: If an unexpected error occurs.
        """
        if follow:
            raise NotImplementedError(
                "Log following is not yet implemented for Cloud Run deployer"
            )

        try:
            existing_metadata = CloudRunDeploymentMetadata.from_deployment(
                deployment
            )
            service_name = existing_metadata.service_name
            if not service_name:
                assert deployment.snapshot, (
                    "Pipeline snapshot not set for deployment"
                )
                settings = cast(
                    GCPDeployerSettings,
                    self.get_settings(deployment.snapshot),
                )
                # We rely on the running service name, if a service is currently
                # active. If not, we fall back to the service name generated
                # from the current configuration.
                service_name = self._get_service_name(
                    deployment.name,
                    deployment.id,
                    settings.service_name_prefix,
                )

            filter_str = (
                'resource.type="cloud_run_revision" AND '
                f'resource.labels.service_name="{service_name}"'
            )

            entries = self.logging_client.list_entries(filter_=filter_str)

            log_lines = []
            for entry in entries:
                if hasattr(entry, "payload") and entry.payload:
                    timestamp = (
                        entry.timestamp.isoformat() if entry.timestamp else ""
                    )
                    log_line = f"[{timestamp}] {entry.payload}"
                    log_lines.append(log_line)

            if tail is not None and tail > 0:
                log_lines = log_lines[-tail:]

            for log_line in log_lines:
                yield log_line

        except google_exceptions.GoogleAPICallError as e:
            raise DeploymentLogsNotFoundError(
                f"Failed to retrieve logs for deployment "
                f"'{deployment.name}': {e}"
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
        """Deprovision a Cloud Run deployment.

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
            RuntimeError: If the service name, project ID or location is not
                found in the deployment metadata.
        """
        service = self._get_cloud_run_service(deployment)
        if service is None:
            raise DeploymentNotFoundError(
                f"Cloud Run service for deployment '{deployment.name}' not found"
            )

        try:
            existing_metadata = CloudRunDeploymentMetadata.from_deployment(
                deployment
            )
            if (
                not existing_metadata.service_name
                or not existing_metadata.project_id
                or not existing_metadata.location
            ):
                raise RuntimeError(
                    f"Service name, project ID or location not found in "
                    f"deployment metadata for deployment '{deployment.name}'"
                )

            service_path = self._get_service_path(
                existing_metadata.service_name,
                existing_metadata.project_id,
                existing_metadata.location,
            )

            logger.debug(
                f"Deleting Cloud Run service for deployment '{deployment.name}'"
            )

            self.cloud_run_client.delete_service(name=service_path)

            self._cleanup_deployment_secrets(deployment)

        except google_exceptions.NotFound:
            raise DeploymentNotFoundError(
                f"Cloud Run service for deployment '{deployment.name}' not found"
            )
        except google_exceptions.GoogleAPICallError as e:
            raise DeploymentDeprovisionError(
                f"Failed to delete Cloud Run service for deployment "
                f"'{deployment.name}': {e}"
            )
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while deleting deployment "
                f"'{deployment.name}': {e}"
            )

        return self.do_get_deployment_state(deployment)
