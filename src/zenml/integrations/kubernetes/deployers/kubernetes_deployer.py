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
from kubernetes import config as k8s_config
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
from zenml.integrations.kubernetes.k8s_applier import (
    KubernetesApplier,
    ResourceInventoryItem,
)
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
    PipelineSnapshotResponse,
)
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)

MAX_LOAD_BALANCER_TIMEOUT = 600  # 10 minutes


class _DeploymentCtx(BaseModel):
    """Deployment context."""

    settings: KubernetesDeployerSettings
    snapshot: PipelineSnapshotResponse
    namespace: str
    resource_name: str
    deployment_id: str
    labels: Dict[str, str]
    secret_name: str
    image: str

    model_config = ConfigDict(frozen=True)


class KubernetesDeployer(ContainerizedDeployer):
    """Kubernetes deployer using template-based resource management."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Kubernetes deployer.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init__(**kwargs)

        self._k8s_client: Optional[k8s_client.ApiClient] = None
        self._applier: Optional[KubernetesApplier] = None

    # ========================================================================
    # Kubernetes Client Management
    # ========================================================================

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Getter for the Kubernetes API client.

        Args:
            incluster: Whether to use the in-cluster config or not. Overrides
                the `incluster` setting in the config.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: if the Kubernetes connector behaves unexpectedly.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            try:
                kube_utils.load_kube_config(
                    incluster=incluster,
                )
                self._k8s_client = k8s_client.ApiClient()
                return self._k8s_client
            except Exception as e:
                if self.connector:
                    message = (
                        "Falling back to using the linked service connector "
                        "configuration."
                    )
                elif self.config.kubernetes_context:
                    message = (
                        f"Falling back to using the configured "
                        f"'{self.config.kubernetes_context}' kubernetes context."
                    )
                else:
                    raise RuntimeError(
                        f"The orchestrator failed to load the in-cluster "
                        f"Kubernetes configuration and there is no service "
                        f"connector or kubernetes_context to fall back to: {e}"
                    ) from e

                logger.debug(
                    f"Could not load the in-cluster Kubernetes configuration: "
                    f"{e}. {message}"
                )

        # Refresh the client also if the connector has expired
        if self._k8s_client and not self.connector_has_expired():
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
        if self.connector_has_expired():
            self._applier = None

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

    def get_kubernetes_contexts(self) -> Tuple[List[str], str]:
        """Get list of configured Kubernetes contexts and the active context.

        Raises:
            RuntimeError: if the Kubernetes configuration cannot be loaded.

        Returns:
            context_name: List of configured Kubernetes contexts
            active_context_name: Name of the active Kubernetes context.
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

            kubernetes_context = self.config.kubernetes_context
            msg = f"'{self.name}' Kubernetes deployer error: "

            if not self.connector:
                if self.config.incluster:
                    # No service connector or kubernetes_context is needed when
                    # the deployer is being used from within a Kubernetes
                    # cluster.
                    pass
                elif kubernetes_context:
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
                            f"{msg}the Kubernetes context "
                            f"'{kubernetes_context}' configured for the "
                            f"Kubernetes deployer is not the same as the "
                            f"active context in the local Kubernetes "
                            f"configuration. If this is not deliberate, you "
                            f"should update the deployer's "
                            f"`kubernetes_context` field by running:\n\n"
                            f"  `zenml deployer update {self.name} "
                            f"--kubernetes_context={active_context}`\n"
                            f"To list all configured contexts, run:\n\n"
                            f"  `kubectl config get-contexts`\n"
                            f"To set the active context to be the same as the "
                            f"one configured in the Kubernetes deployer "
                            f"and silence this warning, run:\n\n"
                            f"  `kubectl config use-context "
                            f"{kubernetes_context}`\n"
                        )
                else:
                    return False, (
                        f"{msg}you must either link this deployer to a "
                        "Kubernetes service connector (see the 'zenml "
                        "deployer connect' CLI command), explicitly set "
                        "the `kubernetes_context` attribute to the name of the "
                        "Kubernetes config context pointing to the cluster "
                        "where you would like to deploy, or set the "
                        "`incluster` attribute to `True`."
                    )

            silence_local_validations_msg = (
                f"To silence this warning, set the "
                f"`skip_local_validations` attribute to True in the "
                f"deployer configuration by running:\n\n"
                f"  'zenml deployer update {self.name} "
                f"--skip_local_validations=True'\n"
            )

            if (
                not self.config.skip_local_validations
                and not self.config.is_local
            ):
                # If the deployer is not running in a local k3d cluster,
                # we cannot have any other local components in our stack,
                # because we cannot mount the local path into the container.
                # This may result in problems when running deployments, because
                # the local components will not be available inside the
                # kubernetes containers.

                # Go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running deployments.
                for stack_comp in stack.components.values():
                    if stack_comp.local_path is None:
                        continue
                    return False, (
                        f"{msg}the Kubernetes deployer is configured to "
                        f"run deployments in a remote Kubernetes cluster but the "
                        f"'{stack_comp.name}' {stack_comp.type.value} "
                        f"is a local stack component "
                        f"and will not be available in the Kubernetes deployment "
                        f"containers.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Kubernetes deployer, "
                        f"otherwise you may run into deployment execution "
                        f"problems. You should use a flavor of "
                        f"{stack_comp.type.value} other than "
                        f"'{stack_comp.flavor}'.\n"
                        + silence_local_validations_msg
                    )

                # If the deployer is remote, the container registry must
                # also be remote.
                if container_registry.config.is_local:
                    return False, (
                        f"{msg}the Kubernetes deployer is configured to "
                        "run deployments in a remote Kubernetes cluster but the "
                        f"'{container_registry.name}' container registry URI "
                        f"'{container_registry.config.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubernetes deployer, otherwise you will "
                        f"run into problems. You should use a flavor of "
                        f"container registry other than "
                        f"'{container_registry.flavor}'.\n"
                        + silence_local_validations_msg
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
            replicas: Number of replicas.
            deployment_id: Optional deployment UUID for unique resource naming.

        Returns:
            Template context dictionary.
        """
        resources = {}
        if resource_requests:
            resources["requests"] = resource_requests

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
            pod_settings_for_template = settings.pod_settings.model_copy(
                update={"env": settings.pod_settings.env + secret_env_list}
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
            "image_pull_secrets": settings.image_pull_secrets,
            "service_account_name": settings.service_account_name,
            "command": settings.command,
            "args": settings.args,
            "env": env_vars,
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
            "service_type": settings.service_type,
            "service_port": settings.service_port,
            "target_port": settings.service_port,
            "pod_settings": pod_settings_for_template,
        }

        return context

    def _get_template_path(
        self, builtin_name: str, custom_path: Optional[str]
    ) -> str:
        """Get template path (custom or built-in).

        Args:
            builtin_name: Name of built-in template file.
            custom_path: Optional custom template path.

        Returns:
            Path to the template file.
        """
        if custom_path:
            return custom_path

        from pathlib import Path

        builtin_dir = Path(__file__).parent.parent / "templates" / "kubernetes"
        return str(builtin_dir / builtin_name)

    # ========================================================================
    # Secret Key Validation
    # ========================================================================

    def _validate_secret_key(
        self,
        key: str,
        secret_key_map: Dict[str, str],
        existing_env_vars: Optional[Dict[str, str]] = None,
    ) -> str:
        """Validate secret key is a valid K8s env var name and check for collisions.

        Args:
            key: Original secret key name.
            secret_key_map: Dictionary tracking validated key mappings to detect collisions.
            existing_env_vars: Optional dictionary of existing environment variables
                to check for collisions.

        Returns:
            The validated secret key name.

        Raises:
            DeploymentProvisionError: If key is invalid or causes a collision.
        """
        # Kubernetes env var names must match: [A-Za-z_][A-Za-z0-9_]*
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            raise DeploymentProvisionError(
                f"Secret key '{key}' is not a valid Kubernetes environment variable name. "
                f"It must start with a letter or underscore and contain only letters, "
                f"numbers, and underscores. Please rename the secret."
            )

        if key in secret_key_map and secret_key_map[key] != key:
            raise DeploymentProvisionError(
                f"Secret key '{key}' already exists as another secret. "
                f"Please use unique secret names."
            )

        if existing_env_vars and key in existing_env_vars:
            raise DeploymentProvisionError(
                f"Secret key '{key}' conflicts with an existing environment variable. "
                f"Please rename the secret to avoid collision."
            )

        secret_key_map[key] = key
        return key

    # ========================================================================
    # Provisioning
    # ========================================================================

    def _wait_for_deployment_readiness(
        self,
        ctx: _DeploymentCtx,
        timeout: int,
    ) -> None:
        """Wait for deployment and service to become ready.

        Args:
            ctx: The deployment context.
            timeout: Timeout in seconds.

        Raises:
            DeploymentProvisionError: If deployment doesn't become ready in time.
        """
        if timeout <= 0:
            return

        try:
            logger.info(
                f"Waiting for deployment to become ready...\n"
                f"  Deployment: {ctx.resource_name}\n"
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
                f"Deployment '{ctx.resource_name}' did not become ready: {e}"
            ) from e

        if (
            ctx.settings.service_type == "LoadBalancer"
            and ctx.settings.wait_for_load_balancer_timeout > 0
        ):
            try:
                lb_timeout = min(
                    timeout,
                    ctx.settings.wait_for_load_balancer_timeout,
                    MAX_LOAD_BALANCER_TIMEOUT,
                )
                logger.info(
                    f"Waiting for LoadBalancer IP (timeout: {lb_timeout}s)..."
                )
                self.k8s_applier.wait_for_service_loadbalancer_ip(
                    name=ctx.resource_name,
                    namespace=ctx.namespace,
                    timeout=lb_timeout,
                    check_interval=ctx.settings.deployment_ready_check_interval,
                )
                logger.info("LoadBalancer IP assigned")
            except RuntimeError:
                logger.warning(
                    f"LoadBalancer IP not assigned within {lb_timeout}s. "
                    f"Service may still be accessible via cluster IP."
                )

    def _cleanup_failed_deployment(self, ctx: _DeploymentCtx) -> None:
        """Cleanup resources after deployment failure.

        Args:
            ctx: The deployment context.
        """
        label_selector = f"zenml-deployment-id={ctx.deployment_id}"
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

    def _initialize_deployment_context(
        self, deployment: DeploymentResponse
    ) -> _DeploymentCtx:
        """Initialize basic deployment context from deployment snapshot.

        Sets up instance variables: _settings, _namespace, _resource_name,
        _labels, and _engine (if needed).

        Args:
            deployment: The deployment to initialize context for.

        Raises:
            DeployerError: If deployment has no snapshot.

        Returns:
            The deployment context.
        """
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no snapshot"
            )

        settings = cast(
            KubernetesDeployerSettings, self.get_settings(snapshot)
        )
        deployment_id = str(deployment.id)
        resource_name = kube_utils.sanitize_label(f"zenml-{deployment_id}")
        secret_name = resource_name

        labels = {
            "zenml-deployment-id": deployment_id,
            "zenml-deployment-name": kube_utils.sanitize_label(
                deployment.name
            ),
            "managed-by": "zenml",
        }
        if settings.labels:
            labels.update(**settings.labels)

        image = self.get_image(snapshot)

        return _DeploymentCtx(
            settings=settings,
            snapshot=snapshot,
            namespace=settings.namespace,
            deployment_id=deployment_id,
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
    ) -> Tuple[_DeploymentCtx, List[Dict[str, Any]]]:
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
        ctx = self._initialize_deployment_context(deployment)
        engine = KubernetesTemplateEngine()

        try:
            resource_requests, replicas = (
                kube_utils.convert_resource_settings_to_k8s_format(
                    ctx.snapshot.pipeline_configuration.resource_settings
                )
            )
        except ValueError as e:
            raise DeploymentProvisionError(
                f"Invalid resource settings for deployment '{deployment.name}': {e}"
            ) from e

        secret_key_map: Dict[str, str] = {}
        validated_secrets = {}
        for key, value in secrets.items():
            validated_key = self._validate_secret_key(
                key, secret_key_map, environment
            )
            validated_secrets[validated_key] = value

        context = self._build_template_context(
            settings=ctx.settings,
            resource_name=ctx.resource_name,
            namespace=ctx.namespace,
            labels=ctx.labels,
            image=ctx.image,
            env_vars=environment,
            secret_env_vars=validated_secrets,
            secret_name=ctx.secret_name,
            resource_requests=resource_requests,
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

        rendered_resources: List[Dict[str, Any]] = [
            build_namespace_manifest(
                namespace=ctx.namespace, labels=ctx.labels
            )
        ]

        if validated_secrets:
            secret_manifest = build_secret_manifest(
                name=ctx.secret_name,
                data=validated_secrets,
                namespace=ctx.namespace,
            )
            rendered_resources.append(
                self.k8s_applier.api_client.sanitize_for_serialization(
                    secret_manifest
                )
            )

        deployment_template = self._get_template_path(
            "deployment.yaml.j2", ctx.settings.custom_deployment_template_file
        )
        rendered_resources.extend(
            engine.render_template(deployment_template, context)
        )

        service_template = self._get_template_path(
            "service.yaml.j2", ctx.settings.custom_service_template_file
        )
        rendered_resources.extend(
            engine.render_template(service_template, context)
        )

        for additional_resource in ctx.settings.additional_resources or []:
            try:
                rendered_resources.extend(
                    engine.render_template(additional_resource, context)
                )
            except Exception as e:
                error_msg = f"Failed to render additional resource '{additional_resource}': {e}"
                if ctx.settings.strict_additional_resources:
                    raise DeploymentProvisionError(error_msg) from e
                else:
                    logger.warning(
                        f"{error_msg}. Skipping (strict_additional_resources=False)"
                    )

        return ctx, rendered_resources

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
        ctx, rendered_resources = self._prepare_deployment_resources(
            deployment, environment, secrets
        )

        try:
            created_objects, inventory = self.k8s_applier.provision(
                rendered_resources,
                default_namespace=ctx.namespace,
                timeout=timeout,
            )
            logger.info(
                f"Successfully created {len(created_objects)} Kubernetes resource(s)"
            )

            self._wait_for_deployment_readiness(
                ctx=ctx,
                timeout=timeout,
            )

            state = self.do_get_deployment_state(deployment)

            if state.metadata is None:
                state.metadata = {}
            state.metadata["resource_inventory"] = [
                item.model_dump() for item in inventory
            ]

            return state

        except Exception as e:
            try:
                self._cleanup_failed_deployment(ctx=ctx)
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

        This method requires both the Deployment and Service resources to be present.
        If either is missing, it raises DeploymentNotFoundError. This behavior treats
        a partially present deployment as "not found" rather than distinguishing
        between "missing", "partially created", or "misconfigured" states.

        Args:
            deployment: The deployment.

        Returns:
            The operational state.

        Raises:
            DeployerError: If deployment has no snapshot.
            DeploymentNotFoundError: If deployment not found or either the Deployment
                or Service resource is missing.
        """
        ctx = self._initialize_deployment_context(deployment)

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

            stored_metadata = deployment.deployment_metadata
            if stored_metadata and "resource_inventory" in stored_metadata:
                metadata["resource_inventory"] = stored_metadata[
                    "resource_inventory"
                ]

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
        """Get deployment logs from the first pod only.

        Args:
            deployment: The deployment.
            follow: Whether to follow logs.
            tail: Number of lines to tail.

        Yields:
            Log lines from the first pod matching the deployment label.

        Raises:
            DeploymentLogsNotFoundError: If no pods are found for the deployment.
        """
        ctx = self._initialize_deployment_context(deployment)

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
        """Deprovision a deployment using inventory-based deletion.

        Args:
            deployment: The deployment to deprovision.
            timeout: Timeout in seconds.

        Returns:
            None to indicate immediate deletion.

        Raises:
            DeploymentDeprovisionError: If deprovisioning fails.
        """
        ctx = self._initialize_deployment_context(deployment)

        try:
            stored_metadata = deployment.deployment_metadata
            inventory_data = (
                stored_metadata.get("resource_inventory")
                if stored_metadata
                else None
            )

            if not inventory_data:
                label_selector = f"zenml-deployment-id={deployment.id}"
                logger.info(
                    f"Deprovisioning deployment '{deployment.name}' using "
                    f"label selector (no inventory found)"
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

            inventory = [
                ResourceInventoryItem(**item) for item in inventory_data
            ]
            logger.info(
                f"Deprovisioning deployment '{deployment.name}' "
                f"({len(inventory)} resources)"
            )

            deleted_count = self.k8s_applier.delete_from_inventory(
                inventory=inventory,
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
                logger.info(
                    f"Deployment '{deployment.name}' not found (already deleted)"
                )
                return None
            raise DeploymentDeprovisionError(
                f"Kubernetes API error while deprovisioning '{deployment.name}': "
                f"{e.status} - {e.reason}"
            ) from e
        except DeploymentDeprovisionError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to deprovision '{deployment.name}': {e}. "
                f"Manual cleanup may be required."
            )
            raise DeploymentDeprovisionError(
                f"Unexpected error deprovisioning '{deployment.name}': {e}"
            ) from e
