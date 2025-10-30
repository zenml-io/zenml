#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from zenml.integrations.kubernetes.kube_utils import (
    build_service_url,
    check_pod_failure_status,
    convert_resource_settings_to_k8s_format,
    create_deployment,
    create_ingress,
    create_or_update_hpa,
    create_service,
    delete_deployment,
    delete_hpa,
    delete_ingress,
    delete_service,
    get_deployment,
    get_hpa,
    get_ingress,
    get_service,
    list_pods,
    service_needs_recreate,
    update_deployment,
    update_ingress,
    update_service,
    wait_for_deployment_ready,
    wait_for_loadbalancer_ip,
    wait_for_service_deletion,
)
from zenml.integrations.kubernetes.manifest_utils import (
    build_deployment_manifest,
    build_ingress_manifest,
    build_service_manifest,
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

    @property
    def k8s_autoscaling_api(self) -> k8s_client.AutoscalingV2Api:
        """Get Kubernetes Autoscaling V2 API client.

        Returns:
            Kubernetes Autoscaling V2 API client.
        """
        return k8s_client.AutoscalingV2Api(self.get_kube_client())

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
            if e.status == 409:
                logger.debug(f"Namespace '{namespace}' already exists.")
            else:
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
                    pass
            elif self.config.incluster:
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
        if deployment.deployment_metadata:
            try:
                metadata = KubernetesDeploymentMetadata.from_deployment(
                    deployment
                )
                return metadata.namespace
            except Exception:
                logger.debug(
                    f"Could not retrieve namespace from metadata for "
                    f"deployment '{deployment.name}', parsing settings instead."
                )

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
        return kube_utils.sanitize_label(name)[:MAX_K8S_NAME_LENGTH]

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

        if settings.labels:
            labels.update(settings.labels)

        return labels

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

        sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", key)

        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"

        if not sanitized:
            raise DeployerError(
                f"Secret key '{original_key}' cannot be sanitized to a valid "
                f"Kubernetes environment variable name. Please use keys that "
                f"contain at least one alphanumeric character."
            )

        if sanitized != original_key:
            logger.warning(
                f"Secret key '{original_key}' was sanitized to '{sanitized}' "
                f"to meet Kubernetes environment variable name requirements. "
                f"The environment variable will be available as '{sanitized}'."
            )

        return sanitized

    def _sanitize_secrets(self, secrets: Dict[str, str]) -> Dict[str, str]:
        """Sanitize secret keys to valid Kubernetes environment variable names.

        Args:
            secrets: Dictionary of secret keys and values.

        Returns:
            Dictionary mapping sanitized keys to values.

        Raises:
            DeployerError: If sanitization causes key collisions.
        """
        sanitized_secrets: Dict[str, str] = {}
        collision_map: Dict[str, str] = {}

        for key, value in secrets.items():
            sanitized_key = self._sanitize_secret_key(key)

            if sanitized_key in collision_map:
                raise DeployerError(
                    f"Secret key collision detected: keys '{collision_map[sanitized_key]}' "
                    f"and '{key}' both sanitize to '{sanitized_key}'. "
                    f"Please rename one of them to avoid conflicts."
                )

            collision_map[sanitized_key] = key
            sanitized_secrets[sanitized_key] = value

        return sanitized_secrets

    def _prepare_environment(
        self,
        deployment: DeploymentResponse,
        environment: Dict[str, str],
        sanitized_secrets: Dict[str, str],
    ) -> List[k8s_client.V1EnvVar]:
        """Prepare environment variables for the container.

        Args:
            deployment: The deployment.
            environment: Environment variables.
            sanitized_secrets: Secret environment variables (keys already sanitized).

        Returns:
            List of Kubernetes environment variables.

        Note:
            Secrets are stored as Kubernetes Secret resources and referenced
            via secretKeyRef for better security. Keys should be pre-sanitized
            using _sanitize_secrets() to avoid duplicate processing.
        """
        env_vars = []

        for key, value in environment.items():
            env_vars.append(k8s_client.V1EnvVar(name=key, value=value))

        if sanitized_secrets:
            secret_name = self._get_secret_name(deployment)
            for key in sanitized_secrets.keys():
                env_vars.append(
                    k8s_client.V1EnvVar(
                        name=key,
                        value_from=k8s_client.V1EnvVarSource(
                            secret_key_ref=k8s_client.V1SecretKeySelector(
                                name=secret_name,
                                key=key,
                            )
                        ),
                    )
                )

        return env_vars

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
            secrets: Secret environment variables (already sanitized).
            settings: Deployer settings.
            resource_requests: Resource requests (cpu, memory, gpu).
            resource_limits: Resource limits (cpu, memory, gpu).
            replicas: Number of pod replicas.

        Returns:
            Kubernetes Deployment manifest.
        """
        deployment_name = self._get_deployment_name(deployment)
        namespace = self._get_namespace(deployment)
        labels = self._get_deployment_labels(deployment, settings)

        env_vars = self._prepare_environment(deployment, environment, secrets)

        command = settings.command or [
            "python",
            "-m",
            "zenml.deployers.server.app",
        ]
        args = settings.args or [
            f"--{DEPLOYMENT_ID_OPTION}",
            str(deployment.id),
        ]

        liveness_probe_config = {
            "initial_delay_seconds": settings.liveness_probe_initial_delay,
            "period_seconds": settings.liveness_probe_period,
            "timeout_seconds": settings.liveness_probe_timeout,
            "failure_threshold": settings.liveness_probe_failure_threshold,
        }
        readiness_probe_config = {
            "initial_delay_seconds": settings.readiness_probe_initial_delay,
            "period_seconds": settings.readiness_probe_period,
            "timeout_seconds": settings.readiness_probe_timeout,
            "failure_threshold": settings.readiness_probe_failure_threshold,
        }

        return build_deployment_manifest(
            deployment_name=deployment_name,
            namespace=namespace,
            labels=labels,
            annotations=settings.annotations,
            replicas=replicas,
            image=image,
            command=command,
            args=args,
            env_vars=env_vars,
            service_port=settings.service_port,
            resource_requests=resource_requests,
            resource_limits=resource_limits,
            image_pull_policy=settings.image_pull_policy,
            image_pull_secrets=settings.image_pull_secrets,
            service_account_name=settings.service_account_name,
            liveness_probe_config=liveness_probe_config,
            readiness_probe_config=readiness_probe_config,
            pod_settings=settings.pod_settings,
        )

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
        service_name = self._get_deployment_name(deployment)
        namespace = self._get_namespace(deployment)
        labels = self._get_deployment_labels(deployment, settings)

        return build_service_manifest(
            service_name=service_name,
            namespace=namespace,
            labels=labels,
            annotations=settings.service_annotations,
            service_type=settings.service_type,
            service_port=settings.service_port,
            node_port=settings.node_port,
            session_affinity=settings.session_affinity,
            load_balancer_ip=settings.load_balancer_ip,
            load_balancer_source_ranges=settings.load_balancer_source_ranges,
        )

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
        service_name = self._get_deployment_name(deployment)
        namespace = self._get_namespace(deployment)
        labels = self._get_deployment_labels(deployment, settings)
        ingress_name = f"{service_name}-ingress"

        if (
            settings.ingress_tls_enabled
            and not settings.ingress_tls_secret_name
        ):
            raise DeployerError(
                "ingress_tls_secret_name must be set when ingress_tls_enabled is True"
            )

        return build_ingress_manifest(
            ingress_name=ingress_name,
            namespace=namespace,
            labels=labels,
            annotations=settings.ingress_annotations,
            service_name=service_name,
            service_port=settings.service_port,
            ingress_class=settings.ingress_class,
            ingress_host=settings.ingress_host,
            ingress_path=settings.ingress_path,
            ingress_path_type=settings.ingress_path_type,
            tls_enabled=settings.ingress_tls_enabled,
            tls_secret_name=settings.ingress_tls_secret_name,
        )

    def _get_ingress_name(self, deployment: DeploymentResponse) -> str:
        """Generate Kubernetes ingress name.

        Args:
            deployment: The deployment.

        Returns:
            Ingress name.
        """
        service_name = self._get_deployment_name(deployment)
        return f"{service_name}-ingress"

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
            pods = list_pods(
                core_api=self.k8s_core_api,
                namespace=namespace,
                label_selector=label_selector,
            )
            if not pods.items:
                return None

            from datetime import datetime, timezone

            sentinel = datetime.min.replace(tzinfo=timezone.utc)

            running_pods = [
                p
                for p in pods.items
                if p.status and p.status.phase == "Running"
            ]
            if running_pods:
                return max(
                    running_pods,
                    key=lambda p: p.metadata.creation_timestamp or sentinel,
                )

            return max(
                pods.items,
                key=lambda p: p.metadata.creation_timestamp or sentinel,
            )
        except ApiException:
            pass

        return None

    def _manage_deployment_secrets(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        secrets: Dict[str, str],
    ) -> Dict[str, str]:
        """Manage Kubernetes secrets for deployment.

        Args:
            deployment: The deployment.
            namespace: Kubernetes namespace.
            secrets: Secret environment variables.

        Returns:
            Sanitized secrets dictionary.
        """
        sanitized_secrets = self._sanitize_secrets(secrets) if secrets else {}
        secret_name = self._get_secret_name(deployment)

        if sanitized_secrets:
            logger.info(
                f"Creating/updating Kubernetes Secret '{secret_name}' "
                f"in namespace '{namespace}'."
            )
            kube_utils.create_or_update_secret(
                core_api=self.k8s_core_api,
                namespace=namespace,
                secret_name=secret_name,
                data=cast(Dict[str, Optional[str]], sanitized_secrets),
            )
        else:
            # Clean up Secret if all secrets were removed
            try:
                kube_utils.delete_secret(
                    core_api=self.k8s_core_api,
                    namespace=namespace,
                    secret_name=secret_name,
                )
                logger.debug(
                    f"Deleted empty Kubernetes Secret '{secret_name}' "
                    f"in namespace '{namespace}'."
                )
            except Exception:
                pass

        return sanitized_secrets

    def _manage_deployment_resource(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        deployment_name: str,
        deployment_manifest: k8s_client.V1Deployment,
        existing_deployment: Optional[k8s_client.V1Deployment],
    ) -> None:
        """Create or update Kubernetes Deployment resource.

        Args:
            deployment: The deployment.
            namespace: Kubernetes namespace.
            deployment_name: Name of the Kubernetes Deployment.
            deployment_manifest: Deployment manifest.
            existing_deployment: Existing deployment if updating.
        """
        if existing_deployment:
            logger.info(
                f"Updating Kubernetes Deployment '{deployment_name}' "
                f"in namespace '{namespace}'."
            )
            update_deployment(
                apps_api=self.k8s_apps_api,
                name=deployment_name,
                namespace=namespace,
                deployment_manifest=deployment_manifest,
            )
        else:
            logger.info(
                f"Creating Kubernetes Deployment '{deployment_name}' "
                f"in namespace '{namespace}'."
            )
            create_deployment(
                apps_api=self.k8s_apps_api,
                namespace=namespace,
                deployment_manifest=deployment_manifest,
            )

    def _manage_service_resource(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        service_name: str,
        service_manifest: k8s_client.V1Service,
        existing_service: Optional[k8s_client.V1Service],
    ) -> None:
        """Create or update Kubernetes Service resource.

        Args:
            deployment: The deployment.
            namespace: Kubernetes namespace.
            service_name: Name of the Kubernetes Service.
            service_manifest: Service manifest.
            existing_service: Existing service if updating.

        Raises:
            DeploymentProvisionError: If service deletion times out.
        """
        if existing_service:
            needs_recreate = service_needs_recreate(
                existing_service, service_manifest
            )

            if needs_recreate:
                logger.info(
                    f"Service '{service_name}' has immutable field changes. "
                    f"Deleting and recreating..."
                )
                delete_service(
                    core_api=self.k8s_core_api,
                    name=service_name,
                    namespace=namespace,
                )
                try:
                    wait_for_service_deletion(
                        core_api=self.k8s_core_api,
                        service_name=service_name,
                        namespace=namespace,
                        timeout=SERVICE_DELETION_TIMEOUT_SECONDS,
                    )
                except RuntimeError as e:
                    raise DeploymentProvisionError(str(e)) from e

                create_service(
                    core_api=self.k8s_core_api,
                    namespace=namespace,
                    service_manifest=service_manifest,
                )
            else:
                logger.info(
                    f"Updating Kubernetes Service '{service_name}' "
                    f"in namespace '{namespace}'."
                )
                update_service(
                    core_api=self.k8s_core_api,
                    name=service_name,
                    namespace=namespace,
                    service_manifest=service_manifest,
                )
        else:
            logger.info(
                f"Creating Kubernetes Service '{service_name}' "
                f"in namespace '{namespace}'."
            )
            create_service(
                core_api=self.k8s_core_api,
                namespace=namespace,
                service_manifest=service_manifest,
            )

    def _manage_ingress_resource(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        settings: KubernetesDeployerSettings,
    ) -> None:
        """Manage Kubernetes Ingress resource.

        Args:
            deployment: The deployment.
            namespace: Kubernetes namespace.
            settings: Deployer settings.
        """
        ingress_name = self._get_ingress_name(deployment)
        existing_ingress = get_ingress(
            networking_api=self.k8s_networking_api,
            name=ingress_name,
            namespace=namespace,
        )

        if settings.ingress_enabled:
            ingress_manifest = self._build_ingress_manifest(
                deployment, settings
            )

            if existing_ingress:
                logger.info(
                    f"Updating Kubernetes Ingress '{ingress_name}' "
                    f"in namespace '{namespace}'."
                )
                update_ingress(
                    networking_api=self.k8s_networking_api,
                    name=ingress_name,
                    namespace=namespace,
                    ingress_manifest=ingress_manifest,
                )
            else:
                logger.info(
                    f"Creating Kubernetes Ingress '{ingress_name}' "
                    f"in namespace '{namespace}'."
                )
                create_ingress(
                    networking_api=self.k8s_networking_api,
                    namespace=namespace,
                    ingress_manifest=ingress_manifest,
                )
        elif existing_ingress:
            # Delete Ingress if disabled
            logger.info(
                f"Ingress disabled, deleting existing Kubernetes Ingress '{ingress_name}' "
                f"in namespace '{namespace}'."
            )
            delete_ingress(
                networking_api=self.k8s_networking_api,
                name=ingress_name,
                namespace=namespace,
            )

    def _manage_hpa_resource(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        deployment_name: str,
        settings: KubernetesDeployerSettings,
    ) -> None:
        """Manage HorizontalPodAutoscaler resource.

        Args:
            deployment: The deployment.
            namespace: Kubernetes namespace.
            deployment_name: Name of the Kubernetes Deployment.
            settings: Deployer settings.
        """
        hpa_name = f"{deployment_name}-hpa"

        if settings.hpa_manifest:
            logger.info(
                f"Creating/updating HorizontalPodAutoscaler "
                f"in namespace '{namespace}'."
            )
            create_or_update_hpa(
                autoscaling_api=self.k8s_autoscaling_api,
                namespace=namespace,
                hpa_manifest=settings.hpa_manifest,
            )
        else:
            # Delete HPA if removed from settings
            existing_hpa = get_hpa(
                autoscaling_api=self.k8s_autoscaling_api,
                name=hpa_name,
                namespace=namespace,
            )
            if existing_hpa:
                logger.info(
                    f"HPA manifest removed, deleting existing HorizontalPodAutoscaler '{hpa_name}' "
                    f"in namespace '{namespace}'."
                )
                delete_hpa(
                    autoscaling_api=self.k8s_autoscaling_api,
                    name=hpa_name,
                    namespace=namespace,
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

        # Convert resource settings to Kubernetes format
        try:
            resource_requests, resource_limits, replicas = (
                convert_resource_settings_to_k8s_format(
                    snapshot.pipeline_configuration.resource_settings
                )
            )
        except ValueError as e:
            raise DeploymentProvisionError(str(e)) from e

        namespace = self._get_namespace(deployment)
        deployment_name = self._get_deployment_name(deployment)
        service_name = deployment_name

        existing_deployment = get_deployment(
            apps_api=self.k8s_apps_api,
            name=deployment_name,
            namespace=namespace,
        )
        is_new_deployment = existing_deployment is None

        try:
            image = self.get_image(snapshot)
            self.ensure_namespace_exists(namespace)

            # Manage secrets
            sanitized_secrets = self._manage_deployment_secrets(
                deployment, namespace, secrets
            )

            # Build manifests
            deployment_manifest = self._build_deployment_manifest(
                deployment,
                image,
                environment,
                sanitized_secrets,
                settings,
                resource_requests,
                resource_limits,
                replicas,
            )
            service_manifest = self._build_service_manifest(
                deployment, settings
            )

            # Manage Kubernetes resources
            self._manage_deployment_resource(
                deployment,
                namespace,
                deployment_name,
                deployment_manifest,
                existing_deployment,
            )

            existing_service = get_service(
                core_api=self.k8s_core_api,
                name=service_name,
                namespace=namespace,
            )
            self._manage_service_resource(
                deployment,
                namespace,
                service_name,
                service_manifest,
                existing_service,
            )

            self._manage_ingress_resource(deployment, namespace, settings)
            self._manage_hpa_resource(
                deployment, namespace, deployment_name, settings
            )

            # Wait for deployment to be ready
            if timeout > 0:
                try:
                    wait_for_deployment_ready(
                        apps_api=self.k8s_apps_api,
                        deployment_name=deployment_name,
                        namespace=namespace,
                        timeout=timeout,
                        check_interval=DEPLOYMENT_READY_CHECK_INTERVAL_SECONDS,
                    )
                except RuntimeError as e:
                    raise DeploymentProvisionError(str(e)) from e

                # Wait for LoadBalancer IP if applicable
                if settings.service_type == "LoadBalancer":
                    lb_timeout = min(timeout, 150)
                    wait_for_loadbalancer_ip(
                        core_api=self.k8s_core_api,
                        service_name=service_name,
                        namespace=namespace,
                        timeout=lb_timeout,
                        check_interval=DEPLOYMENT_READY_CHECK_INTERVAL_SECONDS,
                    )
            else:
                logger.info(
                    f"Deployment '{deployment_name}' created. "
                    f"No timeout specified, not waiting for readiness. "
                    f"Poll deployment state to check readiness."
                )

            return self.do_get_deployment_state(deployment)

        except DeploymentProvisionError:
            # Re-raise deployment errors without cleanup (user may want to inspect state)
            raise
        except Exception as e:
            # For new deployments that failed, clean up to avoid orphaned resources
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

    def _determine_deployment_status(
        self,
        k8s_deployment: k8s_client.V1Deployment,
        deployment: DeploymentResponse,
    ) -> DeploymentStatus:
        """Determine deployment status from Kubernetes Deployment.

        Args:
            k8s_deployment: Kubernetes Deployment resource.
            deployment: ZenML deployment.

        Returns:
            Deployment status.
        """
        status = DeploymentStatus.PENDING

        if k8s_deployment.status:
            available_replicas = k8s_deployment.status.available_replicas or 0
            replicas = k8s_deployment.spec.replicas or 0

            if available_replicas == replicas and replicas > 0:
                status = DeploymentStatus.RUNNING
            elif k8s_deployment.status.ready_replicas:
                status = DeploymentStatus.PENDING
            elif k8s_deployment.status.conditions:
                for condition in k8s_deployment.status.conditions:
                    if (
                        condition.type == "Progressing"
                        and condition.status == "False"
                    ):
                        status = DeploymentStatus.ERROR
                        break

        # Check pod-level failures
        if status != DeploymentStatus.RUNNING:
            pod = self._get_pod_for_deployment(deployment)
            if pod:
                error_reason = check_pod_failure_status(
                    pod, restart_error_threshold=POD_RESTART_ERROR_THRESHOLD
                )
                if error_reason:
                    logger.warning(
                        f"Deployment '{deployment.name}' pod failure detected: {error_reason}"
                    )
                    status = DeploymentStatus.ERROR

        return status

    def _extract_resource_info(
        self, k8s_deployment: k8s_client.V1Deployment
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract resource information from Kubernetes Deployment.

        Args:
            k8s_deployment: Kubernetes Deployment resource.

        Returns:
            Tuple of (cpu, memory, image) as strings or None.
        """
        cpu_str = None
        memory_str = None
        image_str = None

        if (
            k8s_deployment.spec.template.spec.containers
            and k8s_deployment.spec.template.spec.containers[0]
        ):
            container = k8s_deployment.spec.template.spec.containers[0]

            if container.resources:
                if container.resources.requests:
                    cpu_str = container.resources.requests.get("cpu")
                    memory_str = container.resources.requests.get("memory")
                # Fall back to limits if requests not set
                if not cpu_str and container.resources.limits:
                    cpu_str = container.resources.limits.get("cpu")
                if not memory_str and container.resources.limits:
                    memory_str = container.resources.limits.get("memory")

            if container.image:
                image_str = container.image

        return cpu_str, memory_str, image_str

    def _enrich_metadata_with_service_info(
        self,
        metadata: KubernetesDeploymentMetadata,
        k8s_service: k8s_client.V1Service,
        settings: KubernetesDeployerSettings,
    ) -> None:
        """Enrich metadata with service-specific information.

        Args:
            metadata: Deployment metadata to enrich.
            k8s_service: Kubernetes Service resource.
            settings: Deployer settings.
        """
        if settings.service_type == "LoadBalancer":
            if (
                k8s_service.status.load_balancer
                and k8s_service.status.load_balancer.ingress
            ):
                lb_ingress = k8s_service.status.load_balancer.ingress[0]
                metadata.external_ip = lb_ingress.ip or lb_ingress.hostname
        elif settings.service_type == "NodePort":
            if k8s_service.spec.ports:
                metadata.node_port = k8s_service.spec.ports[0].node_port

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
        deployment_name = self._get_deployment_name(deployment)
        ingress_name = self._get_ingress_name(deployment)

        try:
            # Get Kubernetes resources
            k8s_deployment = get_deployment(
                apps_api=self.k8s_apps_api,
                name=deployment_name,
                namespace=namespace,
            )
            k8s_service = get_service(
                core_api=self.k8s_core_api,
                name=deployment_name,
                namespace=namespace,
            )
            k8s_ingress = None
            if settings.ingress_enabled:
                k8s_ingress = get_ingress(
                    networking_api=self.k8s_networking_api,
                    name=ingress_name,
                    namespace=namespace,
                )

            if not k8s_deployment or not k8s_service:
                raise DeploymentNotFoundError(
                    f"Kubernetes resources for deployment '{deployment.name}' "
                    "not found"
                )

            # Determine status
            status = self._determine_deployment_status(
                k8s_deployment, deployment
            )

            # Build URL
            url = build_service_url(
                core_api=self.k8s_core_api,
                service=k8s_service,
                namespace=namespace,
                ingress=k8s_ingress,
            )

            # Extract resource info
            cpu_str, memory_str, image_str = self._extract_resource_info(
                k8s_deployment
            )

            # Get pod name
            pod = self._get_pod_for_deployment(deployment)
            pod_name = pod.metadata.name if pod else None

            # Build metadata
            metadata = KubernetesDeploymentMetadata(
                deployment_name=self._get_deployment_name(deployment),
                namespace=namespace,
                service_name=self._get_deployment_name(deployment),
                pod_name=pod_name,
                port=settings.service_port,
                service_type=settings.service_type,
                replicas=k8s_deployment.spec.replicas or 0,
                ready_replicas=k8s_deployment.status.ready_replicas or 0,
                available_replicas=k8s_deployment.status.available_replicas
                or 0,
                cpu=cpu_str,
                memory=memory_str,
                image=image_str,
                labels=self._get_deployment_labels(deployment, settings),
            )

            # Enrich metadata with service-specific info
            self._enrich_metadata_with_service_info(
                metadata, k8s_service, settings
            )

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
        service_name = self._get_deployment_name(deployment)
        ingress_name = self._get_ingress_name(deployment)

        try:
            # Delete HPA if it exists
            hpa_name = f"{deployment_name}-hpa"
            delete_hpa(
                autoscaling_api=self.k8s_autoscaling_api,
                name=hpa_name,
                namespace=namespace,
            )
            logger.info(
                f"Deleted HorizontalPodAutoscaler '{hpa_name}' "
                f"in namespace '{namespace}'."
            )

            # Delete Ingress
            delete_ingress(
                networking_api=self.k8s_networking_api,
                name=ingress_name,
                namespace=namespace,
            )
            logger.info(
                f"Deleted Kubernetes Ingress '{ingress_name}' "
                f"in namespace '{namespace}'."
            )

            # Delete Service
            delete_service(
                core_api=self.k8s_core_api,
                name=service_name,
                namespace=namespace,
            )
            logger.info(
                f"Deleted Kubernetes Service '{service_name}' "
                f"in namespace '{namespace}'."
            )

            # Delete Deployment
            delete_deployment(
                apps_api=self.k8s_apps_api,
                name=deployment_name,
                namespace=namespace,
                propagation_policy="Foreground",  # Wait for pods to be deleted
            )
            logger.info(
                f"Deleted Kubernetes Deployment '{deployment_name}' "
                f"in namespace '{namespace}'."
            )

            # Delete Secret
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
                if e.status != 404:
                    logger.warning(
                        f"Failed to delete Secret '{secret_name}': {e}"
                    )

            return None

        except ApiException as e:
            if e.status == 404:
                raise DeploymentNotFoundError(
                    f"Kubernetes resources for deployment '{deployment.name}' "
                    "not found"
                )
            else:
                raise DeploymentDeprovisionError(
                    f"Failed to deprovision deployment '{deployment.name}': {e}"
                )
