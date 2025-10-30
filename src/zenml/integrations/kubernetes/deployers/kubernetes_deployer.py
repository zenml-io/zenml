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
"""Implementation of the ZenML Kubernetes deployer."""

import re
import time
from typing import (
    TYPE_CHECKING,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes import watch as k8s_watch
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, Field

from zenml.config.resource_settings import ByteUnit, ResourceSettings
from zenml.deployers.containerized_deployer import (
    ContainerizedDeployer,
)
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
    DeploymentLogsNotFoundError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.deployers.server.entrypoint_configuration import (
    DEPLOYMENT_ID_OPTION,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerConfig,
    KubernetesDeployerSettings,
)
from zenml.integrations.kubernetes.manifest_utils import (
    add_pod_settings,
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

# Resource constants
MAX_K8S_NAME_LENGTH = 63

SERVICE_DELETION_TIMEOUT_SECONDS = 60
INITIAL_BACKOFF_SECONDS = 0.5
MAX_BACKOFF_SECONDS = 5.0
DEPLOYMENT_READY_CHECK_INTERVAL_SECONDS = 2

POD_RESTART_ERROR_THRESHOLD = 2


class KubernetesDeploymentMetadata(BaseModel):
    """Metadata for a Kubernetes deployment.

    Captures runtime state and actual deployment details. Configuration settings
    are stored separately in the deployment snapshot and can be viewed with
    `zenml deployment describe <name> --show-schema`.

    Attributes:
        deployment_name: The name of the Kubernetes Deployment resource.
        namespace: The namespace where the deployment is running.
        service_name: The name of the Kubernetes Service resource.
        pod_name: The name of a running pod (if available).
        port: The service port exposed by the deployment.
        service_type: The type of Kubernetes Service (LoadBalancer, NodePort, ClusterIP).
        external_ip: The external IP or hostname (for LoadBalancer services).
        node_port: The assigned node port (for NodePort services).
        replicas: Number of replicas desired by the deployment.
        ready_replicas: Number of pods that are ready and serving traffic.
        available_replicas: Number of pods available for use.
        cpu: CPU resources allocated to the deployment (e.g., "1000m", "2").
        memory: Memory resources allocated to the deployment (e.g., "2Gi").
        image: The container image actually deployed.
        labels: Labels applied to the deployment resources.
    """

    deployment_name: str
    namespace: str
    service_name: str
    pod_name: Optional[str] = None
    port: int
    service_type: str = "LoadBalancer"
    external_ip: Optional[str] = None
    node_port: Optional[int] = None
    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    available_replicas: Optional[int] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None
    image: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "KubernetesDeploymentMetadata":
        """Create KubernetesDeploymentMetadata from a deployment response.

        Args:
            deployment: The deployment to get the metadata for.

        Returns:
            The metadata for the Kubernetes deployment.

        Raises:
            DeployerError: If the deployment metadata is invalid.
        """
        if not deployment.deployment_metadata:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no metadata."
            )

        try:
            return cls.model_validate(deployment.deployment_metadata)
        except Exception as e:
            raise DeployerError(
                f"Failed to parse deployment metadata for deployment "
                f"'{deployment.name}': {e}"
            )


class KubernetesDeployer(ContainerizedDeployer):
    """Deployer for running pipelines in Kubernetes."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Get authenticated Kubernetes client.

        This method handles:
        - In-cluster authentication
        - Service connector authentication
        - Local kubeconfig authentication
        - Client caching and expiration

        Args:
            incluster: Whether to use in-cluster config. Overrides
                the config setting if provided.

        Returns:
            Authenticated Kubernetes API client.

        Raises:
            RuntimeError: If connector behaves unexpectedly.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        connector_has_expired = self.connector_has_expired()
        if self._k8s_client and not connector_has_expired:
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def k8s_core_api(self) -> k8s_client.CoreV1Api:
        """Get Kubernetes Core V1 API client.

        Returns:
            Kubernetes Core V1 API client.
        """
        return k8s_client.CoreV1Api(self.get_kube_client())

    @property
    def k8s_apps_api(self) -> k8s_client.AppsV1Api:
        """Get Kubernetes Apps V1 API client.

        Returns:
            Kubernetes Apps V1 API client.
        """
        return k8s_client.AppsV1Api(self.get_kube_client())

    @property
    def k8s_batch_api(self) -> k8s_client.BatchV1Api:
        """Get Kubernetes Batch V1 API client.

        Returns:
            Kubernetes Batch V1 API client.
        """
        return k8s_client.BatchV1Api(self.get_kube_client())

    @property
    def k8s_rbac_api(self) -> k8s_client.RbacAuthorizationV1Api:
        """Get Kubernetes RBAC Authorization V1 API client.

        Returns:
            Kubernetes RBAC Authorization V1 API client.
        """
        return k8s_client.RbacAuthorizationV1Api(self.get_kube_client())

    @property
    def k8s_networking_api(self) -> k8s_client.NetworkingV1Api:
        """Get Kubernetes Networking V1 API client.

        Returns:
            Kubernetes Networking V1 API client.
        """
        return k8s_client.NetworkingV1Api(self.get_kube_client())

    def get_kubernetes_contexts(self) -> Tuple[List[str], str]:
        """Get list of configured Kubernetes contexts and the active context.

        Returns:
            Tuple of (context_names, active_context_name).

        Raises:
            RuntimeError: If Kubernetes configuration cannot be loaded.
        """
        try:
            contexts, active_context = k8s_config.list_kube_config_contexts()
        except k8s_config.config_exception.ConfigException as e:
            raise RuntimeError(
                "Could not load the Kubernetes configuration"
            ) from e

        context_names = [c["name"] for c in contexts]
        active_context_name = active_context["name"]
        return context_names, active_context_name

    def ensure_namespace_exists(self, namespace: str) -> None:
        """Ensure a Kubernetes namespace exists.

        Args:
            namespace: The namespace name.

        Raises:
            RuntimeError: If namespace creation fails due to permissions
                or other non-conflict errors.
        """
        try:
            kube_utils.create_namespace(
                core_api=self.k8s_core_api,
                namespace=namespace,
            )
            logger.debug(f"Created namespace '{namespace}'.")
        except ApiException as e:
            # 409 Conflict means namespace already exists, which is fine
            if e.status == 409:
                logger.debug(f"Namespace '{namespace}' already exists.")
            else:
                # Re-raise RBAC/permission errors or other API failures
                raise RuntimeError(
                    f"Failed to ensure namespace '{namespace}' exists: {e}. "
                    f"This may be due to insufficient permissions (RBAC) or "
                    f"cluster configuration issues."
                ) from e

    def create_or_get_service_account(
        self,
        service_account_name: str,
        namespace: str,
        role_binding_name: str = "zenml-edit",
    ) -> str:
        """Create or get a Kubernetes service account with edit permissions.

        Args:
            service_account_name: Name of the service account.
            namespace: Kubernetes namespace.
            role_binding_name: Name of the role binding.

        Returns:
            The service account name.
        """
        kube_utils.create_edit_service_account(
            core_api=self.k8s_core_api,
            rbac_api=self.k8s_rbac_api,
            service_account_name=service_account_name,
            namespace=namespace,
            role_binding_name=role_binding_name,
        )
        return service_account_name

    def validate_kubernetes_context(
        self, stack: "Stack", component_type: str
    ) -> Tuple[bool, str]:
        """Validate Kubernetes context configuration.

        Args:
            stack: The stack to validate.
            component_type: Type of component (e.g., "orchestrator", "deployer").

        Returns:
            Tuple of (is_valid, error_message).
        """
        container_registry = stack.container_registry
        assert container_registry is not None

        kubernetes_context = self.config.kubernetes_context
        msg = f"'{self.name}' Kubernetes {component_type} error: "

        if not self.connector:
            if kubernetes_context:
                try:
                    contexts, active_context = self.get_kubernetes_contexts()

                    if kubernetes_context not in contexts:
                        return False, (
                            f"{msg}could not find a Kubernetes context named "
                            f"'{kubernetes_context}' in the local "
                            "Kubernetes configuration. Please make sure that "
                            "the Kubernetes cluster is running and that the "
                            "kubeconfig file is configured correctly. To list "
                            "all configured contexts, run:\n\n"
                            "  `kubectl config get-contexts`\n"
                        )
                    if kubernetes_context != active_context:
                        logger.warning(
                            f"{msg}the Kubernetes context '{kubernetes_context}' "
                            f"configured for the Kubernetes {component_type} is not "
                            f"the same as the active context in the local Kubernetes "
                            f"configuration. To set the active context, run:\n\n"
                            f"  `kubectl config use-context {kubernetes_context}`\n"
                        )
                except Exception:
                    # If we can't load kube config, that's okay - might be in-cluster
                    pass
            elif self.config.incluster:
                # No service connector or kubernetes_context needed when
                # running from within a Kubernetes cluster
                pass
            else:
                return False, (
                    f"{msg}you must either link this {component_type} to a "
                    "Kubernetes service connector (see the 'zenml "
                    f"{component_type} connect' CLI command), explicitly set "
                    "the `kubernetes_context` attribute to the name of the "
                    "Kubernetes config context pointing to the cluster "
                    "where you would like to run operations, or set the "
                    "`incluster` attribute to `True`."
                )

        # If the component is remote, the container registry must also be remote
        if not self.config.is_local and container_registry.config.is_local:
            return False, (
                f"{msg}the Kubernetes {component_type} is configured to "
                "run in a remote Kubernetes cluster but the "
                f"'{container_registry.name}' container registry URI "
                f"'{container_registry.config.uri}' points to a local "
                f"container registry. Please ensure that you use a remote "
                f"container registry with a remote Kubernetes {component_type}."
            )

        return True, ""

    @property
    def config(self) -> KubernetesDeployerConfig:
        """Get the Kubernetes deployer config.

        Returns:
            The Kubernetes deployer config.
        """
        return cast(KubernetesDeployerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type[KubernetesDeployerSettings]]:
        """Return the settings class for the Kubernetes deployer.

        Returns:
            The settings class.
        """
        return KubernetesDeployerSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validator for the Kubernetes deployer.

        Returns:
            Stack validator.
        """

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that the stack is compatible with Kubernetes deployer.

            Args:
                stack: The stack.

            Returns:
                Whether the stack is valid and an explanation if not.
            """
            # Use mixin's validation method
            return self.validate_kubernetes_context(stack, "deployer")

        return StackValidator(
            required_components={
                StackComponentType.IMAGE_BUILDER,
                StackComponentType.CONTAINER_REGISTRY,
            },
            custom_validation_function=_validate_local_requirements,
        )

    def _get_namespace(self, deployment: DeploymentResponse) -> str:
        """Get the namespace for a deployment.

        Attempts to retrieve namespace from cached metadata first for performance,
        then falls back to parsing settings if metadata is unavailable.

        Args:
            deployment: The deployment.

        Returns:
            Namespace name.

        Raises:
            DeployerError: If the deployment has no snapshot.
        """
        # Fast path: Try to get namespace from metadata (avoids re-parsing settings)
        if deployment.deployment_metadata:
            try:
                metadata = KubernetesDeploymentMetadata.from_deployment(
                    deployment
                )
                return metadata.namespace
            except Exception:
                # Metadata invalid or incomplete, fall back to settings
                logger.debug(
                    f"Could not retrieve namespace from metadata for "
                    f"deployment '{deployment.name}', parsing settings instead."
                )

        # Slow path: Parse settings (used during initial provisioning
        # or when metadata is unavailable)
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no snapshot."
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )
        return settings.namespace or self.config.kubernetes_namespace

    def _get_deployment_name(self, deployment: DeploymentResponse) -> str:
        """Generate Kubernetes deployment name.

        Args:
            deployment: The deployment.

        Returns:
            Sanitized deployment name.
        """
        name = f"zenml-deployment-{deployment.id}"
        # Sanitize for K8s naming rules and limit length
        return kube_utils.sanitize_label(name)[:MAX_K8S_NAME_LENGTH]

    def _get_service_name(self, deployment: DeploymentResponse) -> str:
        """Generate Kubernetes service name.

        Args:
            deployment: The deployment.

        Returns:
            Service name (same as deployment name).
        """
        return self._get_deployment_name(deployment)

    def _get_secret_name(self, deployment: DeploymentResponse) -> str:
        """Generate Kubernetes secret name for deployment secrets.

        Args:
            deployment: The deployment.

        Returns:
            Secret name.
        """
        return f"zenml-secrets-{deployment.id}"

    def _get_deployment_labels(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
    ) -> Dict[str, str]:
        """Get labels for Kubernetes resources.

        Args:
            deployment: The deployment.
            settings: Deployer settings.

        Returns:
            Labels dictionary.
        """
        labels = {
            "zenml-deployment-id": str(deployment.id),
            "zenml-deployment-name": kube_utils.sanitize_label(
                deployment.name
            ),
            "zenml-deployer-id": str(self.id),
            "managed-by": "zenml",
        }

        # Add custom labels from settings
        if settings.labels:
            labels.update(settings.labels)

        return labels

    def _ensure_namespace(self, namespace: str) -> None:
        """Ensure namespace exists. Delegates to mixin method.

        Args:
            namespace: Namespace name.
        """
        # Use mixin's namespace management
        self.ensure_namespace_exists(namespace)

    def _get_log_context(self, namespace: str) -> str:
        """Get context string for log messages.

        Args:
            namespace: Kubernetes namespace.

        Returns:
            Formatted context string for logging (e.g., "[context=my-cluster, namespace=default]").
        """
        context_parts = []
        if self.config.kubernetes_context:
            context_parts.append(f"context={self.config.kubernetes_context}")
        context_parts.append(f"namespace={namespace}")
        return f"[{', '.join(context_parts)}]"

    def _sanitize_secret_key(self, key: str) -> str:
        """Sanitize a secret key to be a valid Kubernetes environment variable name.

        Kubernetes environment variable names must:
        - Consist of alphanumeric characters, '-', '_' or '.'
        - Start with a letter or underscore (not a digit)
        - Not contain certain special characters

        Args:
            key: The secret key to sanitize.

        Returns:
            Sanitized key that is valid as a Kubernetes env var name.

        Raises:
            DeployerError: If the key cannot be sanitized to a valid name.
        """
        original_key = key

        # Replace invalid characters with underscores
        # Valid chars are: alphanumeric, '-', '_', '.'
        sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", key)

        # Ensure it doesn't start with a digit (prepend underscore if needed)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"

        # Ensure it's not empty after sanitization
        if not sanitized:
            raise DeployerError(
                f"Secret key '{original_key}' cannot be sanitized to a valid "
                f"Kubernetes environment variable name. Please use keys that "
                f"contain at least one alphanumeric character."
            )

        # Warn if we had to modify the key
        if sanitized != original_key:
            logger.warning(
                f"Secret key '{original_key}' was sanitized to '{sanitized}' "
                f"to meet Kubernetes environment variable name requirements. "
                f"The environment variable will be available as '{sanitized}'."
            )

        return sanitized

    def _prepare_environment(
        self,
        deployment: DeploymentResponse,
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> List[k8s_client.V1EnvVar]:
        """Prepare environment variables for the container.

        Args:
            deployment: The deployment.
            environment: Environment variables.
            secrets: Secret environment variables (keys will be sanitized).

        Returns:
            List of Kubernetes environment variables.

        Raises:
            DeployerError: If secret key sanitization causes collisions.

        Note:
            Secrets are stored as Kubernetes Secret resources and referenced
            via secretKeyRef for better security. Secret keys are automatically
            sanitized to meet Kubernetes environment variable naming requirements.
        """
        env_vars = []

        # Regular environment variables (plaintext)
        for key, value in environment.items():
            env_vars.append(k8s_client.V1EnvVar(name=key, value=value))

        # Secrets referenced from Kubernetes Secret resource
        if secrets:
            secret_name = self._get_secret_name(deployment)
            # Track sanitized keys to detect collisions
            sanitized_map: Dict[str, str] = {}

            for key in secrets.keys():
                # Sanitize the key to be a valid Kubernetes env var name
                sanitized_key = self._sanitize_secret_key(key)

                # Check for collisions
                if sanitized_key in sanitized_map:
                    raise DeployerError(
                        f"Secret key collision detected: keys '{sanitized_map[sanitized_key]}' "
                        f"and '{key}' both sanitize to '{sanitized_key}'. "
                        f"Please rename one of them to avoid conflicts."
                    )
                sanitized_map[sanitized_key] = key

                env_vars.append(
                    k8s_client.V1EnvVar(
                        name=sanitized_key,
                        value_from=k8s_client.V1EnvVarSource(
                            secret_key_ref=k8s_client.V1SecretKeySelector(
                                name=secret_name,
                                key=sanitized_key,
                            )
                        ),
                    )
                )

        return env_vars

    def _convert_resource_settings_to_k8s_format(
        self,
        resource_settings: ResourceSettings,
    ) -> Tuple[Dict[str, str], Dict[str, str], int]:
        """Convert ResourceSettings to Kubernetes resource format.

        Args:
            resource_settings: The resource settings from pipeline configuration.

        Returns:
            Tuple of (requests, limits, replicas) in Kubernetes format.
            - requests: Dict with 'cpu' and 'memory' keys for resource requests
            - limits: Dict with 'cpu' and 'memory' keys for resource limits
            - replicas: Number of replicas
        """
        # Default resource values
        cpu_request = "100m"
        cpu_limit = "1000m"
        memory_request = "256Mi"
        memory_limit = "2Gi"

        # Convert CPU if specified
        if resource_settings.cpu_count is not None:
            cpu_value = resource_settings.cpu_count
            # Kubernetes accepts fractional CPUs as millicores or as decimal
            # We'll use string format for consistency
            if cpu_value < 1:
                # Convert to millicores for values < 1
                cpu_str = f"{int(cpu_value * 1000)}m"
            else:
                # For >= 1, use the number directly or as millicores
                if cpu_value == int(cpu_value):
                    cpu_str = str(int(cpu_value))
                else:
                    cpu_str = f"{int(cpu_value * 1000)}m"

            # Use same value for request and limit if only one is specified
            cpu_request = cpu_str
            cpu_limit = cpu_str

        # Convert memory if specified
        if resource_settings.memory is not None:
            # ResourceSettings uses formats like "2GB", "512Mi" etc.
            # Kubernetes prefers Mi, Gi format
            memory_value = resource_settings.get_memory(unit=ByteUnit.MIB)
            if memory_value is not None:
                if memory_value >= 1024:
                    # Convert to Gi for readability
                    memory_str = f"{memory_value / 1024:.0f}Gi"
                else:
                    memory_str = f"{memory_value:.0f}Mi"

                # Use same value for request and limit
                memory_request = memory_str
                memory_limit = memory_str

        # Determine replicas from min_replicas/max_replicas
        # For Kubernetes Deployment (non-autoscaling), we use a fixed replica count
        # If min_replicas == max_replicas, use that value
        # Otherwise, use min_replicas as the baseline (HPA would handle max)
        replicas = 1  # Default
        if resource_settings.min_replicas is not None:
            if resource_settings.max_replicas is not None and (
                resource_settings.min_replicas
                == resource_settings.max_replicas
            ):
                # Fixed scaling
                replicas = resource_settings.min_replicas
            else:
                # Variable scaling - use min_replicas as baseline
                # (HPA would be needed for actual autoscaling)
                replicas = resource_settings.min_replicas
        elif resource_settings.max_replicas is not None:
            # Only max specified - use it as fixed value
            if resource_settings.max_replicas > 0:
                replicas = resource_settings.max_replicas

        requests = {
            "cpu": cpu_request,
            "memory": memory_request,
        }

        limits = {
            "cpu": cpu_limit,
            "memory": memory_limit,
        }

        return requests, limits, replicas

    def _build_deployment_manifest(
        self,
        deployment: DeploymentResponse,
        image: str,
        environment: Dict[str, str],
        secrets: Dict[str, str],
        settings: KubernetesDeployerSettings,
        resource_requests: Dict[str, str],
        resource_limits: Dict[str, str],
        replicas: int,
    ) -> k8s_client.V1Deployment:
        """Build Kubernetes Deployment manifest.

        Args:
            deployment: The deployment.
            image: Container image URI.
            environment: Environment variables.
            secrets: Secret environment variables.
            settings: Deployer settings.
            resource_requests: Resource requests (cpu, memory).
            resource_limits: Resource limits (cpu, memory).
            replicas: Number of pod replicas.

        Returns:
            Kubernetes Deployment manifest.
        """
        deployment_name = self._get_deployment_name(deployment)
        namespace = self._get_namespace(deployment)
        labels = self._get_deployment_labels(deployment, settings)
        env_vars = self._prepare_environment(deployment, environment, secrets)

        # Build container spec
        # Use custom command/args if provided, otherwise use defaults
        command = settings.command or [
            "python",
            "-m",
            "zenml.deployers.server.app",
        ]
        args = settings.args or [
            f"--{DEPLOYMENT_ID_OPTION}",
            str(deployment.id),
        ]

        container = k8s_client.V1Container(
            name="deployment",
            image=image,
            command=command,
            args=args,
            env=env_vars,
            ports=[
                k8s_client.V1ContainerPort(
                    container_port=settings.service_port,
                    name="http",
                )
            ],
            resources=k8s_client.V1ResourceRequirements(
                requests=resource_requests,
                limits=resource_limits,
            ),
            liveness_probe=k8s_client.V1Probe(
                http_get=k8s_client.V1HTTPGetAction(
                    path="/api/health",
                    port=settings.service_port,
                ),
                initial_delay_seconds=settings.liveness_probe_initial_delay,
                period_seconds=settings.liveness_probe_period,
                timeout_seconds=settings.liveness_probe_timeout,
                failure_threshold=settings.liveness_probe_failure_threshold,
            ),
            readiness_probe=k8s_client.V1Probe(
                http_get=k8s_client.V1HTTPGetAction(
                    path="/api/health",
                    port=settings.service_port,
                ),
                initial_delay_seconds=settings.readiness_probe_initial_delay,
                period_seconds=settings.readiness_probe_period,
                timeout_seconds=settings.readiness_probe_timeout,
                failure_threshold=settings.readiness_probe_failure_threshold,
            ),
            image_pull_policy=settings.image_pull_policy,
        )

        # Build pod spec
        pod_spec = k8s_client.V1PodSpec(
            containers=[container],
            service_account_name=settings.service_account_name,
            image_pull_secrets=[
                k8s_client.V1LocalObjectReference(name=secret_name)
                for secret_name in settings.image_pull_secrets
            ]
            if settings.image_pull_secrets
            else None,
        )

        # Apply pod_settings if provided
        if settings.pod_settings:
            add_pod_settings(
                pod_spec=pod_spec,
                settings=settings.pod_settings,
            )

        # Build pod template
        pod_template = k8s_client.V1PodTemplateSpec(
            metadata=k8s_client.V1ObjectMeta(
                labels=labels,
                annotations=settings.annotations or None,
            ),
            spec=pod_spec,
        )

        # Build deployment
        deployment_manifest = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name=deployment_name,
                namespace=namespace,
                labels=labels,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=replicas,
                selector=k8s_client.V1LabelSelector(
                    match_labels={
                        "zenml-deployment-id": str(deployment.id),
                    }
                ),
                template=pod_template,
            ),
        )

        return deployment_manifest

    def _build_service_manifest(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
    ) -> k8s_client.V1Service:
        """Build Kubernetes Service manifest.

        Args:
            deployment: The deployment.
            settings: Deployer settings.

        Returns:
            Kubernetes Service manifest.
        """
        service_name = self._get_service_name(deployment)
        namespace = self._get_namespace(deployment)
        labels = self._get_deployment_labels(deployment, settings)

        # Build service port
        service_port = k8s_client.V1ServicePort(
            port=settings.service_port,
            target_port=settings.service_port,
            protocol="TCP",
            name="http",
        )

        # Add node port if service type is NodePort
        if settings.service_type == "NodePort" and settings.node_port:
            service_port.node_port = settings.node_port

        # Build service spec
        service_spec = k8s_client.V1ServiceSpec(
            type=settings.service_type,
            selector={
                "zenml-deployment-id": str(deployment.id),
            },
            ports=[service_port],
        )

        # Add session affinity if specified
        if settings.session_affinity:
            service_spec.session_affinity = settings.session_affinity

        # Add LoadBalancer-specific settings
        if settings.service_type == "LoadBalancer":
            if settings.load_balancer_ip:
                service_spec.load_balancer_ip = settings.load_balancer_ip
            if settings.load_balancer_source_ranges:
                service_spec.load_balancer_source_ranges = (
                    settings.load_balancer_source_ranges
                )

        # Build service
        service_manifest = k8s_client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=k8s_client.V1ObjectMeta(
                name=service_name,
                namespace=namespace,
                labels=labels,
                annotations=settings.service_annotations or None,
            ),
            spec=service_spec,
        )

        return service_manifest

    def _build_ingress_manifest(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
    ) -> k8s_client.V1Ingress:
        """Build Kubernetes Ingress manifest.

        Args:
            deployment: The deployment.
            settings: Deployer settings.

        Returns:
            Kubernetes Ingress manifest.

        Raises:
            DeployerError: If TLS is enabled but secret name is not provided.
        """
        service_name = self._get_service_name(deployment)
        namespace = self._get_namespace(deployment)
        labels = self._get_deployment_labels(deployment, settings)
        ingress_name = f"{service_name}-ingress"

        # Validate TLS configuration
        if (
            settings.ingress_tls_enabled
            and not settings.ingress_tls_secret_name
        ):
            raise DeployerError(
                "ingress_tls_secret_name must be set when ingress_tls_enabled is True"
            )

        # Build path
        path_type = settings.ingress_path_type
        path = settings.ingress_path

        # Build backend
        backend = k8s_client.V1IngressBackend(
            service=k8s_client.V1IngressServiceBackend(
                name=service_name,
                port=k8s_client.V1ServiceBackendPort(
                    number=settings.service_port
                ),
            )
        )

        # Build HTTP rule
        http_ingress_path = k8s_client.V1HTTPIngressPath(
            path=path,
            path_type=path_type,
            backend=backend,
        )

        http_ingress_rule_value = k8s_client.V1HTTPIngressRuleValue(
            paths=[http_ingress_path]
        )

        # Build ingress rule
        ingress_rule = k8s_client.V1IngressRule(
            http=http_ingress_rule_value,
        )

        # Add host if specified
        if settings.ingress_host:
            ingress_rule.host = settings.ingress_host

        # Build TLS configuration if enabled
        tls_configs = None
        if settings.ingress_tls_enabled:
            tls_config = k8s_client.V1IngressTLS(
                secret_name=settings.ingress_tls_secret_name,
            )
            # Add hosts to TLS config if specified
            if settings.ingress_host:
                tls_config.hosts = [settings.ingress_host]
            tls_configs = [tls_config]

        # Build ingress spec
        ingress_spec = k8s_client.V1IngressSpec(
            rules=[ingress_rule],
            tls=tls_configs,
        )

        # Add ingress class if specified
        if settings.ingress_class:
            ingress_spec.ingress_class_name = settings.ingress_class

        # Build ingress
        ingress_manifest = k8s_client.V1Ingress(
            api_version="networking.k8s.io/v1",
            kind="Ingress",
            metadata=k8s_client.V1ObjectMeta(
                name=ingress_name,
                namespace=namespace,
                labels=labels,
                annotations=settings.ingress_annotations or None,
            ),
            spec=ingress_spec,
        )

        return ingress_manifest

    def _get_ingress_name(self, deployment: DeploymentResponse) -> str:
        """Generate Kubernetes ingress name.

        Args:
            deployment: The deployment.

        Returns:
            Ingress name.
        """
        service_name = self._get_service_name(deployment)
        return f"{service_name}-ingress"

    def _build_deployment_url(
        self,
        service: k8s_client.V1Service,
        namespace: str,
        ingress: Optional[k8s_client.V1Ingress] = None,
    ) -> Optional[str]:
        """Build the URL for accessing the deployment.

        Args:
            service: Kubernetes service.
            namespace: Namespace name.
            ingress: Kubernetes Ingress (if enabled).

        Returns:
            Deployment URL or None if not yet available.
        """
        # If ingress is configured, use ingress URL
        if ingress:
            # Determine protocol (http or https)
            protocol = "https" if ingress.spec.tls else "http"

            # Get host from ingress rule
            if ingress.spec.rules:
                rule = ingress.spec.rules[0]
                if rule.host and rule.http and rule.http.paths:
                    # Use explicit host from ingress with path
                    path = rule.http.paths[0].path or "/"
                    return f"{protocol}://{rule.host}{path}"

            # Check ingress status for assigned address
            if ingress.status and ingress.status.load_balancer:
                if ingress.status.load_balancer.ingress:
                    lb_ingress = ingress.status.load_balancer.ingress[0]
                    host = lb_ingress.ip or lb_ingress.hostname
                    if host:
                        path = "/"
                        if (
                            ingress.spec.rules
                            and ingress.spec.rules[0].http
                            and ingress.spec.rules[0].http.paths
                        ):
                            path = (
                                ingress.spec.rules[0].http.paths[0].path or "/"
                            )
                        return f"{protocol}://{host}{path}"

            # Ingress exists but not ready yet
            return None

        # Fall back to service URL
        service_type = service.spec.type
        service_port = service.spec.ports[0].port

        if service_type == "LoadBalancer":
            # Wait for external IP
            if (
                service.status.load_balancer
                and service.status.load_balancer.ingress
            ):
                ingress = service.status.load_balancer.ingress[0]
                host = ingress.ip or ingress.hostname
                if host:
                    return f"http://{host}:{service_port}"
            return None  # LoadBalancer not ready yet

        elif service_type == "NodePort":
            # Get node IP and NodePort
            node_port = service.spec.ports[0].node_port
            if not node_port:
                return None

            # WARNING: NodePort exposure has limitations in many cluster configurations:
            # - Nodes may not have external IPs (private clusters)
            # - Node IPs may not be publicly reachable (firewall rules)
            # - No built-in load balancing across nodes
            # Consider using LoadBalancer or Ingress for production deployments.
            logger.warning(
                "Using NodePort service type. The returned URL may not be "
                "reachable if nodes lack external IPs or are behind firewalls. "
                "Consider using service_type='LoadBalancer' or configuring an "
                "Ingress for production use."
            )

            # Get any node's external IP
            try:
                nodes = self.k8s_core_api.list_node()
                # Try external IP first
                for node in nodes.items:
                    if node.status and node.status.addresses:
                        for address in node.status.addresses:
                            if address.type == "ExternalIP":
                                return f"http://{address.address}:{node_port}"

                # Fallback to internal IP (likely not reachable externally)
                logger.warning(
                    "No nodes with ExternalIP found, using InternalIP. "
                    "This URL is likely only reachable from within the cluster."
                )
                for node in nodes.items:
                    if node.status and node.status.addresses:
                        for address in node.status.addresses:
                            if address.type == "InternalIP":
                                return f"http://{address.address}:{node_port}"
            except Exception as e:
                logger.warning(f"Failed to get node IPs: {e}")
                return None

        elif service_type == "ClusterIP":
            # Internal cluster URL
            return f"http://{service.metadata.name}.{namespace}.svc.cluster.local:{service_port}"

        return None

    def _get_k8s_deployment(
        self, deployment: DeploymentResponse
    ) -> Optional[k8s_client.V1Deployment]:
        """Get Kubernetes Deployment resource.

        Args:
            deployment: The deployment.

        Returns:
            Kubernetes Deployment or None if not found.

        Raises:
            ApiException: If the deployment is not found.
        """
        deployment_name = self._get_deployment_name(deployment)
        namespace = self._get_namespace(deployment)

        try:
            return self.k8s_apps_api.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def _get_k8s_service(
        self, deployment: DeploymentResponse
    ) -> Optional[k8s_client.V1Service]:
        """Get Kubernetes Service resource.

        Args:
            deployment: The deployment.

        Returns:
            Kubernetes Service or None if not found.

        Raises:
            ApiException: If the service is not found.
        """
        service_name = self._get_service_name(deployment)
        namespace = self._get_namespace(deployment)

        try:
            return self.k8s_core_api.read_namespaced_service(
                name=service_name,
                namespace=namespace,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def _get_k8s_ingress(
        self, deployment: DeploymentResponse
    ) -> Optional[k8s_client.V1Ingress]:
        """Get Kubernetes Ingress resource.

        Args:
            deployment: The deployment.

        Returns:
            Kubernetes Ingress or None if not found.

        Raises:
            ApiException: If the ingress is not found.
        """
        ingress_name = self._get_ingress_name(deployment)
        namespace = self._get_namespace(deployment)

        try:
            return self.k8s_networking_api.read_namespaced_ingress(
                name=ingress_name,
                namespace=namespace,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def _get_pod_for_deployment(
        self, deployment: DeploymentResponse
    ) -> Optional[k8s_client.V1Pod]:
        """Get a pod for the deployment.

        Prefers running pods over pending or terminating ones.

        Args:
            deployment: The deployment.

        Returns:
            Pod or None if not found.
        """
        namespace = self._get_namespace(deployment)
        label_selector = f"zenml-deployment-id={deployment.id}"

        try:
            pods = self.k8s_core_api.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
            )
            if not pods.items:
                return None

            from datetime import datetime, timezone

            sentinel = datetime.min.replace(tzinfo=timezone.utc)

            # Prefer running pods (for log access during rolling updates)
            running_pods = [
                p
                for p in pods.items
                if p.status and p.status.phase == "Running"
            ]
            if running_pods:
                # Return most recent running pod
                return max(
                    running_pods,
                    key=lambda p: p.metadata.creation_timestamp or sentinel,
                )

            # If no running pods, return the most recent pod regardless of phase
            return max(
                pods.items,
                key=lambda p: p.metadata.creation_timestamp or sentinel,
            )
        except ApiException:
            pass

        return None

    def _service_needs_recreate(
        self,
        existing_service: k8s_client.V1Service,
        new_manifest: k8s_client.V1Service,
    ) -> bool:
        """Check if a Service needs to be recreated due to immutable field changes.

        Args:
            existing_service: The existing Service from the cluster.
            new_manifest: The new Service manifest to apply.

        Returns:
            True if the Service needs to be deleted and recreated, False otherwise.
        """
        # Service.spec.type is immutable - changing it requires recreate
        existing_type = existing_service.spec.type
        new_type = new_manifest.spec.type
        if existing_type != new_type:
            logger.debug(
                f"Service type changed from {existing_type} to {new_type}, "
                f"requires recreate"
            )
            return True

        # ClusterIP is immutable (except for "None" for headless services)
        existing_cluster_ip = existing_service.spec.cluster_ip
        new_cluster_ip = new_manifest.spec.cluster_ip
        if (
            existing_cluster_ip
            and new_cluster_ip
            and existing_cluster_ip != new_cluster_ip
            and existing_cluster_ip != "None"
            and new_cluster_ip != "None"
        ):
            logger.debug(
                f"Service clusterIP changed from {existing_cluster_ip} to "
                f"{new_cluster_ip}, requires recreate"
            )
            return True

        # NodePort is immutable when set - changing requires recreate
        if existing_type == "NodePort" or new_type == "NodePort":
            existing_ports = existing_service.spec.ports or []
            new_ports = new_manifest.spec.ports or []

            # Create maps of port name/targetPort -> nodePort
            existing_node_ports = {
                (p.name or str(p.port), p.target_port): p.node_port
                for p in existing_ports
                if p.node_port
            }
            new_node_ports = {
                (p.name or str(p.port), p.target_port): p.node_port
                for p in new_ports
                if p.node_port
            }

            # Check if any existing nodePort would change
            for key, existing_node_port in existing_node_ports.items():
                if (
                    key in new_node_ports
                    and new_node_ports[key] != existing_node_port
                ):
                    logger.debug(
                        f"Service nodePort changed for {key}, requires recreate"
                    )
                    return True

        return False

    def _check_pod_failure_status(
        self, pod: k8s_client.V1Pod
    ) -> Optional[str]:
        """Check if a pod has container failures indicating deployment errors.

        Args:
            pod: The Kubernetes pod to inspect.

        Returns:
            Error reason if pod has failures, None otherwise.
        """
        if not pod.status or not pod.status.container_statuses:
            return None

        # Error reasons that indicate permanent or recurring failures
        ERROR_REASONS = {
            "CrashLoopBackOff",
            "ErrImagePull",
            "ImagePullBackOff",
            "CreateContainerConfigError",
            "InvalidImageName",
            "CreateContainerError",
            "RunContainerError",
        }

        for container_status in pod.status.container_statuses:
            # Check waiting state (pod hasn't started successfully)
            if container_status.state and container_status.state.waiting:
                reason = container_status.state.waiting.reason
                if reason in ERROR_REASONS:
                    message = container_status.state.waiting.message or ""
                    return f"{reason}: {message}".strip(": ")

            # Check terminated state (pod crashed)
            if container_status.state and container_status.state.terminated:
                reason = container_status.state.terminated.reason
                exit_code = container_status.state.terminated.exit_code
                # Non-zero exit code indicates failure
                if exit_code and exit_code != 0:
                    message = container_status.state.terminated.message or ""
                    return f"Container terminated with exit code {exit_code}: {reason} {message}".strip()

            # Check last terminated state (for restart info)
            if (
                container_status.last_state
                and container_status.last_state.terminated
            ):
                # If container is restarting frequently, it's likely in CrashLoopBackOff
                restart_count = container_status.restart_count or 0
                if (
                    restart_count > POD_RESTART_ERROR_THRESHOLD
                ):  # Multiple restarts indicate a problem
                    reason = (
                        container_status.last_state.terminated.reason
                        or "Error"
                    )
                    exit_code = (
                        container_status.last_state.terminated.exit_code
                    )
                    return f"Container restarting ({restart_count} restarts): {reason} (exit code {exit_code})"

        return None

    def _wait_for_service_deletion(
        self,
        service_name: str,
        namespace: str,
        timeout: Optional[int] = None,
    ) -> None:
        """Wait for a Service to be fully deleted.

        Polls the Service until it returns 404, indicating deletion is complete.
        This prevents race conditions when recreating Services with immutable
        field changes.

        Args:
            service_name: Name of the Service to wait for.
            namespace: Namespace containing the Service.
            timeout: Maximum time to wait in seconds. If not provided,
                uses SERVICE_DELETION_TIMEOUT_SECONDS.

        Raises:
            DeploymentProvisionError: If Service is not deleted within timeout.
            ApiException: If an API error occurs.
        """
        if timeout is None:
            timeout = SERVICE_DELETION_TIMEOUT_SECONDS

        start_time = time.time()
        backoff = INITIAL_BACKOFF_SECONDS
        max_backoff = MAX_BACKOFF_SECONDS

        while time.time() - start_time < timeout:
            try:
                # Try to read the Service
                self.k8s_core_api.read_namespaced_service(
                    name=service_name,
                    namespace=namespace,
                )
                # Service still exists, wait and retry
                logger.debug(
                    f"Waiting for Service '{service_name}' deletion to complete..."
                )
                time.sleep(backoff)
                # Exponential backoff
                backoff = min(backoff * 1.5, max_backoff)
            except ApiException as e:
                if e.status == 404:
                    # Service is deleted
                    logger.debug(
                        f"Service '{service_name}' deletion confirmed."
                    )
                    return
                # Other errors (permission, etc.) - re-raise
                raise

        # Timeout reached
        raise DeploymentProvisionError(
            f"Timeout waiting for Service '{service_name}' to be deleted. "
            f"Service may have finalizers or the cluster may be slow. "
            f"Check Service status with kubectl."
        )

    def _wait_for_deployment_ready(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> None:
        """Wait for a deployment to become ready.

        Args:
            deployment: The deployment to wait for.
            timeout: Maximum time to wait in seconds.

        Raises:
            DeploymentProvisionError: If deployment doesn't become ready
                within the timeout period.
        """
        deployment_name = self._get_deployment_name(deployment)
        namespace = self._get_namespace(deployment)

        logger.info(
            f"Waiting up to {timeout}s for deployment '{deployment_name}' "
            f"to become ready..."
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                k8s_deployment = self.k8s_apps_api.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace,
                )

                if k8s_deployment.status:
                    available_replicas = (
                        k8s_deployment.status.available_replicas or 0
                    )
                    replicas = k8s_deployment.spec.replicas or 0

                    if available_replicas == replicas and replicas > 0:
                        logger.info(
                            f"Deployment '{deployment_name}' is ready with "
                            f"{available_replicas}/{replicas} replicas available."
                        )
                        return

                    # Check for error conditions
                    if k8s_deployment.status.conditions:
                        for condition in k8s_deployment.status.conditions:
                            if (
                                condition.type == "Progressing"
                                and condition.status == "False"
                                and condition.reason
                                == "ProgressDeadlineExceeded"
                            ):
                                raise DeploymentProvisionError(
                                    f"Deployment '{deployment_name}' failed to "
                                    f"progress: {condition.message}"
                                )

                    logger.debug(
                        f"Deployment '{deployment_name}' status: "
                        f"{available_replicas}/{replicas} replicas available"
                    )

            except ApiException as e:
                if e.status != 404:
                    raise DeploymentProvisionError(
                        f"Error checking deployment status: {e}"
                    ) from e

            time.sleep(DEPLOYMENT_READY_CHECK_INTERVAL_SECONDS)

        # Timeout reached
        raise DeploymentProvisionError(
            f"Deployment '{deployment_name}' did not become ready "
            f"within {timeout} seconds"
        )

    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Provision a Kubernetes deployment.

        Args:
            deployment: The deployment to provision.
            stack: The stack to use for provisioning.
            environment: Environment variables.
            secrets: Secret environment variables.
            timeout: Timeout in seconds.

        Returns:
            The operational state of the deployment.

        Raises:
            DeploymentProvisionError: If provisioning fails.
        """
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeploymentProvisionError(
                f"Deployment '{deployment.name}' has no snapshot."
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )

        # Get resource settings from pipeline configuration
        resource_settings = snapshot.pipeline_configuration.resource_settings

        # Convert resource settings to Kubernetes format
        resource_requests, resource_limits, replicas = (
            self._convert_resource_settings_to_k8s_format(resource_settings)
        )

        namespace = self._get_namespace(deployment)
        deployment_name = self._get_deployment_name(deployment)
        service_name = self._get_service_name(deployment)

        # Track if this is a new deployment (for cleanup purposes)
        existing_deployment = self._get_k8s_deployment(deployment)
        is_new_deployment = existing_deployment is None

        try:
            # Get container image
            image = self.get_image(snapshot)

            # Ensure namespace exists
            self._ensure_namespace(namespace)

            # Create or update Kubernetes Secret for sensitive env vars
            if secrets:
                secret_name = self._get_secret_name(deployment)
                logger.info(
                    f"Creating/updating Kubernetes Secret '{secret_name}' "
                    f"in namespace '{namespace}'."
                )
                # Sanitize secret keys to be valid Kubernetes env var names
                sanitized_secrets = {
                    self._sanitize_secret_key(key): value
                    for key, value in secrets.items()
                }
                # Cast to match expected type (Dict[str, Optional[str]])
                # All str values are valid Optional[str] values
                kube_utils.create_or_update_secret(
                    core_api=self.k8s_core_api,
                    namespace=namespace,
                    secret_name=secret_name,
                    data=cast(Dict[str, Optional[str]], sanitized_secrets),
                )

            # Build manifests
            deployment_manifest = self._build_deployment_manifest(
                deployment,
                image,
                environment,
                secrets,
                settings,
                resource_requests,
                resource_limits,
                replicas,
            )
            service_manifest = self._build_service_manifest(
                deployment, settings
            )

            # Check if resources exist
            existing_service = self._get_k8s_service(deployment)

            # Create or update Deployment
            if existing_deployment:
                logger.info(
                    f"Updating Kubernetes Deployment '{deployment_name}' "
                    f"in namespace '{namespace}'."
                )
                self.k8s_apps_api.patch_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace,
                    body=deployment_manifest,
                )
            else:
                logger.info(
                    f"Creating Kubernetes Deployment '{deployment_name}' "
                    f"in namespace '{namespace}'."
                )
                self.k8s_apps_api.create_namespaced_deployment(
                    namespace=namespace,
                    body=deployment_manifest,
                )

            # Create or update Service
            if existing_service:
                # Check if service type or other immutable fields changed
                needs_recreate = self._service_needs_recreate(
                    existing_service, service_manifest
                )

                if needs_recreate:
                    logger.info(
                        f"Service '{service_name}' has immutable field changes. "
                        f"Deleting and recreating..."
                    )
                    self.k8s_core_api.delete_namespaced_service(
                        name=service_name,
                        namespace=namespace,
                    )
                    # Wait for deletion to complete before recreating
                    # This prevents 409 Conflict errors from racing with finalizers
                    self._wait_for_service_deletion(
                        service_name=service_name,
                        namespace=namespace,
                    )
                    self.k8s_core_api.create_namespaced_service(
                        namespace=namespace,
                        body=service_manifest,
                    )
                else:
                    logger.info(
                        f"Updating Kubernetes Service '{service_name}' "
                        f"in namespace '{namespace}'."
                    )
                    self.k8s_core_api.patch_namespaced_service(
                        name=service_name,
                        namespace=namespace,
                        body=service_manifest,
                    )
            else:
                logger.info(
                    f"Creating Kubernetes Service '{service_name}' "
                    f"in namespace '{namespace}'."
                )
                self.k8s_core_api.create_namespaced_service(
                    namespace=namespace,
                    body=service_manifest,
                )

            # Create or update Ingress if enabled
            if settings.ingress_enabled:
                ingress_name = self._get_ingress_name(deployment)
                ingress_manifest = self._build_ingress_manifest(
                    deployment, settings
                )
                existing_ingress = self._get_k8s_ingress(deployment)

                if existing_ingress:
                    logger.info(
                        f"Updating Kubernetes Ingress '{ingress_name}' "
                        f"in namespace '{namespace}'."
                    )
                    self.k8s_networking_api.patch_namespaced_ingress(
                        name=ingress_name,
                        namespace=namespace,
                        body=ingress_manifest,
                    )
                else:
                    logger.info(
                        f"Creating Kubernetes Ingress '{ingress_name}' "
                        f"in namespace '{namespace}'."
                    )
                    self.k8s_networking_api.create_namespaced_ingress(
                        namespace=namespace,
                        body=ingress_manifest,
                    )
            else:
                # Delete existing Ingress if ingress is now disabled
                # This prevents dangling public endpoints
                ingress_name = self._get_ingress_name(deployment)
                existing_ingress = self._get_k8s_ingress(deployment)

                if existing_ingress:
                    logger.info(
                        f"Ingress disabled, deleting existing Kubernetes Ingress '{ingress_name}' "
                        f"in namespace '{namespace}'."
                    )
                    try:
                        self.k8s_networking_api.delete_namespaced_ingress(
                            name=ingress_name,
                            namespace=namespace,
                        )
                        logger.info(
                            f"Deleted Kubernetes Ingress '{ingress_name}' "
                            f"in namespace '{namespace}'."
                        )
                    except ApiException as e:
                        if e.status != 404:  # Ignore if already deleted
                            logger.warning(
                                f"Failed to delete Ingress '{ingress_name}': {e}"
                            )

            # Wait for deployment to become ready if timeout is specified
            if timeout > 0:
                self._wait_for_deployment_ready(deployment, timeout)
            else:
                logger.info(
                    f"Deployment '{deployment_name}' created. "
                    f"No timeout specified, not waiting for readiness. "
                    f"Poll deployment state to check readiness."
                )

            # Get and return current state
            return self.do_get_deployment_state(deployment)

        except DeploymentProvisionError:
            # Re-raise deployment-specific errors without cleanup
            # (these are expected errors, user may want to inspect state)
            raise
        except Exception as e:
            # For new deployments that failed, attempt cleanup to avoid orphaned resources
            if is_new_deployment:
                logger.error(
                    f"Provisioning failed for new deployment '{deployment.name}'. "
                    f"Attempting cleanup of partial resources..."
                )
                try:
                    self.do_deprovision_deployment(
                        deployment, timeout=SERVICE_DELETION_TIMEOUT_SECONDS
                    )
                    logger.info(
                        f"Successfully cleaned up partial resources for deployment '{deployment.name}'."
                    )
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to clean up partial resources for deployment '{deployment.name}': "
                        f"{cleanup_error}. Manual cleanup may be required."
                    )
            else:
                logger.error(
                    f"Provisioning update failed for deployment '{deployment.name}'. "
                    f"Previous deployment state may still be active."
                )

            raise DeploymentProvisionError(
                f"Failed to provision Kubernetes deployment "
                f"'{deployment.name}': {e}"
            ) from e

    def do_get_deployment_state(
        self,
        deployment: DeploymentResponse,
    ) -> DeploymentOperationalState:
        """Get the state of a Kubernetes deployment.

        Args:
            deployment: The deployment.

        Returns:
            The operational state of the deployment.

        Raises:
            DeploymentNotFoundError: If deployment is not found.
            DeployerError: If the deployment has no snapshot.
        """
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no snapshot."
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )
        namespace = self._get_namespace(deployment)

        try:
            # Get Kubernetes resources
            k8s_deployment = self._get_k8s_deployment(deployment)
            k8s_service = self._get_k8s_service(deployment)
            k8s_ingress = None
            if settings.ingress_enabled:
                k8s_ingress = self._get_k8s_ingress(deployment)

            if not k8s_deployment or not k8s_service:
                raise DeploymentNotFoundError(
                    f"Kubernetes resources for deployment '{deployment.name}' "
                    "not found"
                )

            # Determine status from Deployment-level conditions
            status = DeploymentStatus.PENDING
            if k8s_deployment.status:
                available_replicas = (
                    k8s_deployment.status.available_replicas or 0
                )
                replicas = k8s_deployment.spec.replicas or 0

                if available_replicas == replicas and replicas > 0:
                    status = DeploymentStatus.RUNNING
                elif k8s_deployment.status.ready_replicas:
                    status = DeploymentStatus.PENDING
                elif k8s_deployment.status.conditions:
                    # Check for error conditions
                    for condition in k8s_deployment.status.conditions:
                        if (
                            condition.type == "Progressing"
                            and condition.status == "False"
                        ):
                            status = DeploymentStatus.ERROR
                            break

            # Get pod for additional status checks
            pod = self._get_pod_for_deployment(deployment)
            pod_name = pod.metadata.name if pod else None

            # Check pod-level failures (CrashLoopBackOff, ImagePullBackOff, etc.)
            # These may not be reflected in Deployment conditions
            if status != DeploymentStatus.RUNNING and pod:
                error_reason = self._check_pod_failure_status(pod)
                if error_reason:
                    logger.warning(
                        f"Deployment '{deployment.name}' pod failure detected: {error_reason}"
                    )
                    status = DeploymentStatus.ERROR

            # Build URL (prefer ingress URL if available)
            url = self._build_deployment_url(
                k8s_service, namespace, k8s_ingress
            )

            # Extract runtime resource configuration from deployment
            cpu_str = None
            memory_str = None
            if (
                k8s_deployment.spec.template.spec.containers
                and k8s_deployment.spec.template.spec.containers[0].resources
            ):
                resources = k8s_deployment.spec.template.spec.containers[
                    0
                ].resources
                if resources.requests:
                    cpu_str = resources.requests.get("cpu")
                    memory_str = resources.requests.get("memory")
                # Fall back to limits if no requests
                if not cpu_str and resources.limits:
                    cpu_str = resources.limits.get("cpu")
                if not memory_str and resources.limits:
                    memory_str = resources.limits.get("memory")

            # Get actual image from deployment
            image_str = None
            if (
                k8s_deployment.spec.template.spec.containers
                and k8s_deployment.spec.template.spec.containers[0].image
            ):
                image_str = k8s_deployment.spec.template.spec.containers[
                    0
                ].image

            # Build metadata (runtime state only, config is in snapshot)
            metadata = KubernetesDeploymentMetadata(
                # Core identity
                deployment_name=self._get_deployment_name(deployment),
                namespace=namespace,
                service_name=self._get_service_name(deployment),
                pod_name=pod_name,
                # Service networking
                port=settings.service_port,
                service_type=settings.service_type,
                # Runtime health & scaling
                replicas=k8s_deployment.spec.replicas or 0,
                ready_replicas=k8s_deployment.status.ready_replicas or 0,
                available_replicas=k8s_deployment.status.available_replicas
                or 0,
                # Runtime resources
                cpu=cpu_str,
                memory=memory_str,
                image=image_str,
                # Labels
                labels=self._get_deployment_labels(deployment, settings),
            )

            # Add service-specific networking metadata
            if settings.service_type == "LoadBalancer":
                if (
                    k8s_service.status.load_balancer
                    and k8s_service.status.load_balancer.ingress
                ):
                    ingress = k8s_service.status.load_balancer.ingress[0]
                    metadata.external_ip = ingress.ip or ingress.hostname
            elif settings.service_type == "NodePort":
                if k8s_service.spec.ports:
                    metadata.node_port = k8s_service.spec.ports[0].node_port

            return DeploymentOperationalState(
                status=status,
                url=url,
                metadata=metadata.model_dump(),
            )

        except ApiException as e:
            if e.status == 404:
                raise DeploymentNotFoundError(
                    f"Kubernetes resources for deployment '{deployment.name}' "
                    "not found"
                )
            raise DeployerError(
                f"Failed to get state for deployment '{deployment.name}': {e}"
            )

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get logs from a Kubernetes deployment.

        Args:
            deployment: The deployment.
            follow: Whether to follow the logs.
            tail: Number of lines to tail.

        Yields:
            Log lines.

        Raises:
            DeploymentLogsNotFoundError: If logs cannot be retrieved.

        Note:
            The Generator type signature includes a bool send type for
            compatibility with the base class, though this implementation
            does not currently use sent values.
        """
        namespace = self._get_namespace(deployment)
        pod = self._get_pod_for_deployment(deployment)

        if not pod:
            raise DeploymentLogsNotFoundError(
                f"No pod found for deployment '{deployment.name}'"
            )

        pod_name = pod.metadata.name

        try:
            if follow:
                # Stream logs
                w = k8s_watch.Watch()
                for line in w.stream(
                    self.k8s_core_api.read_namespaced_pod_log,
                    name=pod_name,
                    namespace=namespace,
                    follow=True,
                    tail_lines=tail,
                ):
                    yield line
            else:
                # Get logs synchronously
                logs = self.k8s_core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    tail_lines=tail,
                )
                for line in logs.split("\n"):
                    if line:
                        yield line

        except ApiException as e:
            raise DeploymentLogsNotFoundError(
                f"Failed to retrieve logs for deployment "
                f"'{deployment.name}': {e}"
            )

    def do_deprovision_deployment(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision a Kubernetes deployment.

        Args:
            deployment: The deployment to deprovision.
            timeout: Timeout in seconds.

        Returns:
            None to indicate immediate deletion.

        Raises:
            DeploymentNotFoundError: If deployment is not found.
            DeploymentDeprovisionError: If deprovisioning fails.
        """
        namespace = self._get_namespace(deployment)
        deployment_name = self._get_deployment_name(deployment)
        service_name = self._get_service_name(deployment)
        ingress_name = self._get_ingress_name(deployment)

        try:
            # Delete Ingress first (if it exists)
            try:
                self.k8s_networking_api.delete_namespaced_ingress(
                    name=ingress_name,
                    namespace=namespace,
                )
                logger.info(
                    f"Deleted Kubernetes Ingress '{ingress_name}' "
                    f"in namespace '{namespace}'."
                )
            except ApiException as e:
                if (
                    e.status != 404
                ):  # Ignore if already deleted or never created
                    raise

            # Delete Service (stops traffic)
            try:
                self.k8s_core_api.delete_namespaced_service(
                    name=service_name,
                    namespace=namespace,
                )
                logger.info(
                    f"Deleted Kubernetes Service '{service_name}' "
                    f"in namespace '{namespace}'."
                )
            except ApiException as e:
                if e.status != 404:  # Ignore if already deleted
                    raise

            # Delete Deployment (cascades to pods)
            try:
                self.k8s_apps_api.delete_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace,
                    propagation_policy="Foreground",  # Wait for pods
                )
                logger.info(
                    f"Deleted Kubernetes Deployment '{deployment_name}' "
                    f"in namespace '{namespace}'."
                )
            except ApiException as e:
                if e.status != 404:  # Ignore if already deleted
                    raise

            # Delete Secret (if it exists)
            try:
                secret_name = self._get_secret_name(deployment)
                kube_utils.delete_secret(
                    core_api=self.k8s_core_api,
                    namespace=namespace,
                    secret_name=secret_name,
                )
                logger.info(
                    f"Deleted Kubernetes Secret '{secret_name}' "
                    f"in namespace '{namespace}'."
                )
            except ApiException as e:
                if e.status != 404:  # Ignore if already deleted
                    logger.warning(
                        f"Failed to delete Secret '{secret_name}': {e}"
                    )

            # Return None to indicate immediate deletion
            return None

        except ApiException as e:
            if e.status == 404:
                # Already deleted
                raise DeploymentNotFoundError(
                    f"Kubernetes resources for deployment '{deployment.name}' "
                    "not found"
                )
            else:
                raise DeploymentDeprovisionError(
                    f"Failed to deprovision deployment '{deployment.name}': {e}"
                )
