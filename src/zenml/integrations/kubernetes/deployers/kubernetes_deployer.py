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
"""Kubernetes deployer implementation."""

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

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, ConfigDict

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
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerConfig,
    KubernetesDeployerSettings,
)
from zenml.integrations.kubernetes.k8s_applier import KubernetesApplier
from zenml.integrations.kubernetes.manifest_utils import (
    build_namespace_manifest,
    build_secret_manifest,
)
from zenml.integrations.kubernetes.pod_settings import (
    KubernetesPodSettings,
)
from zenml.integrations.kubernetes.template_engine import (
    KubernetesTemplateEngine,
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

MAX_K8S_NAME_LENGTH = 63
MAX_LOAD_BALANCER_TIMEOUT = 600  # 10 minutes


class _DeploymentCtx(BaseModel):
    """Deployment context."""

    settings: KubernetesDeployerSettings
    namespace: str
    resource_name: str
    labels: Dict[str, str]
    secret_name: str
    image: str

    model_config = ConfigDict(frozen=True)  # immutable once built


class KubernetesDeployer(ContainerizedDeployer):
    """Kubernetes deployer using template-based resource management."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Kubernetes deployer.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init__(**kwargs)

        self._ctx: Optional[_DeploymentCtx] = None
        self._k8s_client: Optional[k8s_client.ApiClient] = None
        self._engine: Optional[KubernetesTemplateEngine] = None
        self._applier: Optional[KubernetesApplier] = None

    def require_ctx(self) -> _DeploymentCtx:
        """Require the deployment context.

        Returns:
            The deployment context.

        Raises:
            DeployerError: If the deployment context is not initialized.
        """
        if self._ctx is None:
            raise DeployerError("Deployment context not initialized.")
        return self._ctx

    # ========================================================================
    # Kubernetes Client Management
    # ========================================================================

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Get authenticated Kubernetes client.

        Args:
            incluster: Whether to use in-cluster config.

        Returns:
            Authenticated Kubernetes API client.

        Raises:
            RuntimeError: If connector returns invalid client type.
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

        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected k8s_client.ApiClient but got {type(client)}"
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
    def k8s_applier(self) -> KubernetesApplier:
        """Get or create Kubernetes Applier instance.

        Returns:
            Kubernetes Applier instance.
        """
        if not self._applier:
            self._applier = KubernetesApplier(
                api_client=self.get_kube_client()
            )
        return self._applier

    # ========================================================================
    # Configuration and Validation
    # ========================================================================

    @property
    def config(self) -> KubernetesDeployerConfig:
        """Get the deployer configuration.

        Returns:
            The deployer configuration.
        """
        return cast(KubernetesDeployerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type[KubernetesDeployerSettings]]:
        """Return the settings class.

        Returns:
            The settings class for this deployer.
        """
        return KubernetesDeployerSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Stack validator for the deployer.

        Returns:
            Stack validator instance.
        """

        def _validate(stack: "Stack") -> Tuple[bool, str]:
            container_registry = stack.container_registry
            if not container_registry:
                return False, "Container registry is required"

            if not self.config.is_local and container_registry.config.is_local:
                return False, (
                    "Cannot use local container registry with remote Kubernetes cluster"
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.IMAGE_BUILDER,
                StackComponentType.CONTAINER_REGISTRY,
            },
            custom_validation_function=_validate,
        )

    # ========================================================================
    # Template Context Building
    # ========================================================================

    def _build_template_context(
        self,
        settings: KubernetesDeployerSettings,
        resource_name: str,
        namespace: str,
        labels: Dict[str, str],
        image: str,
        env_vars: Dict[str, str],
        secret_env_vars: Dict[str, str],
        secret_name: str,
        resource_requests: Dict[str, str],
        resource_limits: Dict[str, str],
        replicas: int,
        deployment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build template rendering context from deployment configuration.

        Args:
            settings: Kubernetes deployer settings.
            resource_name: Sanitized resource name.
            namespace: Kubernetes namespace.
            labels: Resource labels.
            image: Container image.
            env_vars: Environment variables dict.
            secret_env_vars: Secret environment variables dict.
            secret_name: Kubernetes secret name.
            resource_requests: Resource requests dict.
            resource_limits: Resource limits dict.
            replicas: Number of replicas.
            deployment_id: Optional deployment UUID for unique resource naming.

        Returns:
            Template context dictionary.
        """
        resources = {}
        if resource_requests:
            resources["requests"] = resource_requests
        if resource_limits:
            resources["limits"] = resource_limits

        env_dict = dict(env_vars)
        secret_env_list = []
        for key in secret_env_vars.keys():
            secret_env_list.append(
                {
                    "name": key,
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": secret_name,
                            "key": key,
                        }
                    },
                }
            )

        pod_settings_for_template = settings.pod_settings
        if secret_env_list and settings.pod_settings:
            existing_env = list(settings.pod_settings.env or [])
            pod_settings_for_template = settings.pod_settings.model_copy(
                update={"env": existing_env + secret_env_list}
            )
        elif secret_env_list:
            pod_settings_for_template = KubernetesPodSettings(
                env=secret_env_list
            )

        context = {
            "name": resource_name,
            "deployment_name": resource_name,
            "service_name": resource_name,
            "namespace": namespace,
            "deployment_id": deployment_id,
            "labels": labels,
            "annotations": settings.annotations,
            "replicas": replicas,
            "image": image,
            "image_pull_policy": settings.image_pull_policy,
            "image_pull_secrets": settings.image_pull_secrets or [],
            "service_account_name": settings.service_account_name,
            "command": settings.command,
            "args": settings.args,
            "env": env_dict,
            "resources": resources if resources else None,
            "readiness_probe_path": settings.readiness_probe_path,
            "readiness_probe_initial_delay": settings.readiness_probe_initial_delay,
            "readiness_probe_period": settings.readiness_probe_period,
            "readiness_probe_timeout": settings.readiness_probe_timeout,
            "readiness_probe_failure_threshold": settings.readiness_probe_failure_threshold,
            "liveness_probe_path": settings.liveness_probe_path,
            "liveness_probe_initial_delay": settings.liveness_probe_initial_delay,
            "liveness_probe_period": settings.liveness_probe_period,
            "liveness_probe_timeout": settings.liveness_probe_timeout,
            "liveness_probe_failure_threshold": settings.liveness_probe_failure_threshold,
            "probe_port": settings.service_port,
            "security_context": None,
            "service_type": settings.service_type,
            "service_port": settings.service_port,
            "target_port": settings.service_port,
            "pod_settings": pod_settings_for_template,
        }

        return context

    # ========================================================================
    # Secret Key Sanitization
    # ========================================================================

    def _sanitize_secret_key(
        self,
        key: str,
        secret_key_map: Dict[str, str],
        existing_env_vars: Optional[Dict[str, str]] = None,
    ) -> str:
        """Sanitize secret key to valid K8s env var name and detect collisions.

        Args:
            key: Original secret key name.
            secret_key_map: Dictionary tracking sanitized key mappings to detect collisions.
            existing_env_vars: Optional dictionary of existing environment variables
                to check for collisions.

        Returns:
            Sanitized secret key name.

        Raises:
            DeploymentProvisionError: If sanitization causes a collision with an existing key.
        """
        sanitized = re.sub(r"[^A-Za-z0-9_]", "_", key)

        # Ensure starts with letter or underscore
        if sanitized and not re.match(r"^[A-Za-z_]", sanitized):
            sanitized = f"_{sanitized}"
        elif not sanitized:  # Empty after sanitization
            sanitized = "_VAR"

        if sanitized in secret_key_map and secret_key_map[sanitized] != key:
            raise DeploymentProvisionError(
                f"Secret key '{key}' sanitized to '{sanitized}' but already exists "
                f"as another secret key '{secret_key_map[sanitized]}'. "
                f"Please rename one of these secrets to avoid collision."
            )

        if existing_env_vars and sanitized in existing_env_vars:
            raise DeploymentProvisionError(
                f"Secret key '{key}' sanitized to '{sanitized}' but this name "
                f"is already used by an environment variable. "
                f"Please rename the secret to avoid collision."
            )

        secret_key_map[sanitized] = key
        return sanitized

    # ========================================================================
    # Provisioning
    # ========================================================================

    def _wait_for_deployment_readiness(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
        timeout: int,
    ) -> None:
        """Wait for deployment and service to become ready.

        Args:
            deployment: The deployment response.
            settings: Kubernetes deployer settings.
            timeout: Timeout in seconds.

        Raises:
            DeploymentProvisionError: If deployment doesn't become ready in time.
        """
        if timeout <= 0:
            return

        ctx = self.require_ctx()

        try:
            logger.info(
                f"Waiting for deployment to become ready...\n"
                f"  Deployment: {deployment.name}\n"
                f"  Namespace: {ctx.namespace}\n"
                f"  Timeout: {timeout}s"
            )
            self.k8s_applier.wait_for_deployment_ready(
                name=ctx.resource_name,
                namespace=ctx.namespace,
                timeout=timeout,
                check_interval=ctx.settings.deployment_ready_check_interval,
            )
            logger.info("Deployment is ready")
        except RuntimeError as e:
            raise DeploymentProvisionError(
                f"Deployment '{deployment.name}' did not become ready: {e}"
            ) from e

        if (
            settings.service_type == "LoadBalancer"
            and settings.wait_for_load_balancer_timeout > 0
        ):
            try:
                lb_timeout = min(
                    timeout,
                    settings.wait_for_load_balancer_timeout,
                    MAX_LOAD_BALANCER_TIMEOUT,
                )
                logger.info(
                    f"Waiting for LoadBalancer IP (timeout: {lb_timeout}s)..."
                )
                self.k8s_applier.wait_for_service_loadbalancer_ip(
                    name=ctx.resource_name,
                    namespace=ctx.namespace,
                    timeout=lb_timeout,
                    check_interval=settings.deployment_ready_check_interval,
                )
                logger.info("LoadBalancer IP assigned")
            except RuntimeError:
                logger.warning(
                    f"LoadBalancer IP not assigned within {lb_timeout}s. "
                    f"Service may still be accessible via cluster IP."
                )

    def _cleanup_failed_deployment(
        self, deployment: DeploymentResponse
    ) -> None:
        """Cleanup resources after deployment failure.

        Args:
            deployment: The deployment whose resources should be cleaned up.
        """
        ctx = self.require_ctx()
        label_selector = f"zenml-deployment-id={deployment.id}"
        logger.warning(
            f"Provisioning failed, cleaning up resources with label: {label_selector}"
        )
        try:
            deleted_count = self.k8s_applier.delete_by_label_selector(
                label_selector=label_selector,
                namespace=ctx.namespace,
                propagation_policy="Foreground",
            )
            logger.info(f"Cleanup deleted {deleted_count} resource(s)")
        except Exception as cleanup_error:
            logger.error(
                f"Cleanup failed: {cleanup_error}. "
                f"Manual cleanup: kubectl delete all,configmap,secret "
                f"-n {ctx.namespace} -l {label_selector}"
            )

    def _clear_deployment_context(self) -> None:
        """Clear deployment context to prevent state pollution between operations."""
        self._ctx = None
        self._engine = None

    def _initialize_deployment_context(
        self, deployment: DeploymentResponse
    ) -> None:
        """Initialize basic deployment context from deployment snapshot.

        Sets up instance variables: _settings, _namespace, _resource_name,
        _labels, and _engine (if needed).

        Args:
            deployment: The deployment to initialize context for.

        Raises:
            DeployerError: If deployment has no snapshot.
        """
        # Clear any previous context to ensure clean state
        self._clear_deployment_context()

        snapshot = deployment.snapshot
        if not snapshot:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no snapshot"
            )

        settings = cast(
            KubernetesDeployerSettings, self.get_settings(snapshot)
        )
        namespace = settings.namespace or self.config.kubernetes_namespace
        resource_name = kube_utils.sanitize_label(f"zenml-{deployment.id}")[
            :MAX_K8S_NAME_LENGTH
        ]
        secret_name = resource_name

        labels = {
            "zenml-deployment-id": str(deployment.id),
            "zenml-deployment-name": kube_utils.sanitize_label(
                deployment.name
            ),
            "managed-by": "zenml",
        }
        if settings.labels:
            labels.update(**settings.labels)

        image = self.get_image(snapshot)

        self._ctx = _DeploymentCtx(
            settings=settings,
            namespace=namespace,
            resource_name=resource_name,
            secret_name=secret_name,
            labels=labels,
            image=image,
        )

    def _prepare_deployment_resources(
        self,
        deployment: DeploymentResponse,
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Prepare all resources needed for deployment.

        Args:
            deployment: The deployment to prepare.
            environment: Environment variables.
            secrets: Secret environment variables.

        Returns:
            List of rendered kubernetes resources.

        Raises:
            DeploymentProvisionError: If preparation fails.
        """
        snapshot = deployment.snapshot
        assert snapshot, "Pipeline snapshot not found"

        self._initialize_deployment_context(deployment)
        ctx = self.require_ctx()

        self._engine = KubernetesTemplateEngine(
            custom_templates_dir=ctx.settings.custom_templates_dir
            or self.config.custom_templates_dir
        )

        try:
            resource_requests, resource_limits, replicas = (
                kube_utils.convert_resource_settings_to_k8s_format(
                    snapshot.pipeline_configuration.resource_settings
                )
            )
        except ValueError as e:
            raise DeploymentProvisionError(
                f"Invalid resource settings for deployment '{deployment.name}': {e}"
            ) from e

        secret_key_map: Dict[str, str] = {}
        sanitized = {}
        for key, value in secrets.items():
            sanitized_key = self._sanitize_secret_key(
                key, secret_key_map, environment
            )
            sanitized[sanitized_key] = value

        context = self._build_template_context(
            settings=ctx.settings,
            resource_name=ctx.resource_name,
            namespace=ctx.namespace,
            labels=ctx.labels,
            image=ctx.image,
            env_vars=environment,
            secret_env_vars=sanitized,
            secret_name=ctx.secret_name,
            resource_requests=resource_requests,
            resource_limits=resource_limits,
            replicas=replicas,
            deployment_id=str(deployment.id),
        )

        if not context.get("command"):
            context["command"] = cast(
                Any,
                DeploymentEntrypointConfiguration.get_entrypoint_command(),
            )
        if not context.get("args"):
            context["args"] = cast(
                Any,
                DeploymentEntrypointConfiguration.get_entrypoint_arguments(
                    **{DEPLOYMENT_ID_OPTION: deployment.id}
                ),
            )

        # Create namespace with labels to track ownership for cleanup
        rendered_resources: List[Dict[str, Any]] = [
            build_namespace_manifest(
                namespace=ctx.namespace, labels=ctx.labels
            )
        ]

        if sanitized:
            secret_manifest = build_secret_manifest(
                name=ctx.secret_name,
                data=sanitized,
                namespace=ctx.namespace,
            )
            rendered_resources.append(
                self.k8s_applier.api_client.sanitize_for_serialization(
                    secret_manifest
                )
            )

        rendered_resources.extend(
            self._engine.render_template("deployment.yaml.j2", context)
        )
        rendered_resources.extend(
            self._engine.render_template("service.yaml.j2", context)
        )

        for additional_resource in ctx.settings.additional_resources:
            try:
                rendered_resources.extend(
                    self._engine.render_template(additional_resource, context)
                )
            except Exception as e:
                error_msg = f"Failed to render additional resource '{additional_resource}': {e}"
                if ctx.settings.strict_additional_resources:
                    raise DeploymentProvisionError(error_msg) from e
                else:
                    logger.warning(
                        f"{error_msg}. Skipping (strict_additional_resources=False)"
                    )

        return rendered_resources

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
            stack: The stack to use.
            environment: Environment variables.
            secrets: Secret environment variables.
            timeout: Timeout in seconds.

        Returns:
            The operational state of the deployment.

        Raises:
            DeploymentProvisionError: If provisioning fails.
        """
        rendered_resources = self._prepare_deployment_resources(
            deployment, environment, secrets
        )
        ctx = self.require_ctx()

        try:
            created_objects = self.k8s_applier.provision(
                rendered_resources,
                default_namespace=ctx.namespace,
                timeout=timeout,
            )
            logger.info(
                f"Successfully created {len(created_objects)} Kubernetes resource(s)"
            )

            self._wait_for_deployment_readiness(
                deployment,
                ctx.settings,
                timeout,
            )

            return self.do_get_deployment_state(deployment)

        except Exception as e:
            try:
                self._cleanup_failed_deployment(deployment)
            except Exception as cleanup_error:
                logger.error(
                    f"Additional error during cleanup: {cleanup_error}. "
                    f"Original error will be raised."
                )
            raise DeploymentProvisionError(
                f"Failed to provision deployment '{deployment.name}': {e}"
            ) from e

    # ========================================================================
    # State Management
    # ========================================================================

    def do_get_deployment_state(
        self, deployment: DeploymentResponse
    ) -> DeploymentOperationalState:
        """Get deployment state.

        Args:
            deployment: The deployment.

        Returns:
            The operational state.

        Raises:
            DeployerError: If deployment has no snapshot.
            DeploymentNotFoundError: If deployment not found.
        """
        self._initialize_deployment_context(deployment)
        ctx = self.require_ctx()

        try:
            k8s_deployment = self.k8s_applier.get_resource(
                name=ctx.resource_name,
                namespace=ctx.namespace,
                kind="Deployment",
                api_version="apps/v1",
            )
            k8s_service = self.k8s_applier.get_resource(
                name=ctx.resource_name,
                namespace=ctx.namespace,
                kind="Service",
                api_version="v1",
            )

            if not k8s_deployment or not k8s_service:
                raise DeploymentNotFoundError(
                    f"Deployment '{deployment.name}' not found"
                )

            status = DeploymentStatus.PENDING
            if hasattr(k8s_deployment, "to_dict"):
                deployment_dict = k8s_deployment.to_dict()
                status_data = deployment_dict.get("status", {})
                spec_data = deployment_dict.get("spec", {})
                available = status_data.get("availableReplicas", 0)
                desired = spec_data.get("replicas", 0)
            else:
                if k8s_deployment.status:
                    available = k8s_deployment.status.available_replicas or 0
                    desired = k8s_deployment.spec.replicas or 0
                else:
                    available = 0
                    desired = 0

            if available == desired and desired > 0:
                status = DeploymentStatus.RUNNING

            url = kube_utils.build_service_url(
                core_api=self.k8s_core_api,
                service=k8s_service,
                namespace=ctx.namespace,
                ingress=None,
            )

            metadata = {
                "deployment_name": ctx.resource_name,
                "namespace": ctx.namespace,
                "service_name": ctx.resource_name,
                "port": ctx.settings.service_port,
                "service_type": ctx.settings.service_type,
                "labels": ctx.labels,
            }

            return DeploymentOperationalState(
                status=status,
                url=url,
                metadata=metadata,
            )

        except ApiException as e:
            if e.status == 404:
                raise DeploymentNotFoundError(
                    f"Deployment '{deployment.name}' not found"
                )
            raise DeployerError(
                f"Failed to get state for '{deployment.name}': {e}"
            )

    # ========================================================================
    # Logs
    # ========================================================================

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get deployment logs.

        Args:
            deployment: The deployment.
            follow: Whether to follow logs.
            tail: Number of lines to tail.

        Yields:
            Log lines.

        Raises:
            DeploymentLogsNotFoundError: If logs not found.
        """
        self._initialize_deployment_context(deployment)
        ctx = self.require_ctx()

        label_selector = f"zenml-deployment-id={deployment.id}"

        try:
            pods = self.k8s_applier.list_resources(
                namespace=ctx.namespace,
                kind="Pod",
                api_version="v1",
                label_selector=label_selector,
            )
            if not pods:
                raise DeploymentLogsNotFoundError(
                    f"No pods found for deployment '{deployment.name}'"
                )

            pod_name = pods[0].metadata.name

            if follow:
                resp = self.k8s_core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=ctx.namespace,
                    follow=True,
                    tail_lines=tail,
                    _preload_content=False,
                )
                for line in resp:
                    if isinstance(line, bytes):
                        yield line.decode("utf-8").rstrip()
                    else:
                        yield str(line).rstrip()
            else:
                logs = self.k8s_core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=ctx.namespace,
                    tail_lines=tail,
                )
                for line in logs.split("\n"):
                    if line:
                        yield line

        except ApiException as e:
            raise DeploymentLogsNotFoundError(
                f"Failed to get logs for '{deployment.name}': {e}"
            )

    # ========================================================================
    # Deprovisioning
    # ========================================================================

    def do_deprovision_deployment(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision a deployment.

        Uses label selector to delete all resources, which is more robust than
        trying to re-render resources since:
        - Works even if templates or settings have changed
        - Catches any resources we might have missed tracking
        - Handles dependencies correctly with propagation policy

        Args:
            deployment: The deployment to deprovision.
            timeout: Timeout in seconds.

        Returns:
            None to indicate immediate deletion.

        Raises:
            DeploymentDeprovisionError: If deprovisioning fails.
        """
        self._initialize_deployment_context(deployment)
        ctx = self.require_ctx()

        label_selector = f"zenml-deployment-id={deployment.id}"

        try:
            logger.info(
                f"Deprovisioning deployment '{deployment.name}' using label selector: {label_selector}"
            )

            deleted_count = self.k8s_applier.delete_by_label_selector(
                label_selector=label_selector,
                namespace=ctx.namespace,
                propagation_policy="Foreground",
            )

            if deleted_count > 0:
                logger.info(
                    f"Deprovisioned deployment '{deployment.name}' "
                    f"({deleted_count} resource(s) deleted)"
                )
            else:
                logger.info(
                    f"Deployment '{deployment.name}' not found (already deleted)"
                )

            return None

        except ApiException as e:
            if e.status == 404:
                # Resource already gone - that's fine for deprovisioning
                logger.info(
                    f"Deployment '{deployment.name}' not found (already deleted)"
                )
                return None
            raise DeploymentDeprovisionError(
                f"Kubernetes API error while deprovisioning '{deployment.name}': "
                f"{e.status} - {e.reason}"
            ) from e
        except Exception as e:
            logger.error(
                f"Failed to deprovision '{deployment.name}': {e}. "
                f"You may need to manually delete resources:\n"
                f"  kubectl delete all,configmap,secret -n {ctx.namespace} -l {label_selector}"
            )
            raise DeploymentDeprovisionError(
                f"Unexpected error deprovisioning '{deployment.name}': {e}"
            ) from e
