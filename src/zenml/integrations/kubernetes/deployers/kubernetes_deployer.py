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
from zenml.entrypoints.base_entrypoint_configuration import (
    SNAPSHOT_ID_OPTION,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerConfig,
    KubernetesDeployerSettings,
)
from zenml.integrations.kubernetes.k8s_applier import (
    KubernetesApplier,
    ProvisioningError,
    ResourceInventoryItem,
)
from zenml.integrations.kubernetes.manifest_utils import (
    build_namespace_manifest,
    build_secret_manifest,
)
from zenml.integrations.kubernetes.pod_settings import (
    KubernetesPodSettings,
)
from zenml.integrations.kubernetes.serialization_utils import (
    normalize_resource_to_dict,
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
                        warning_msg = "".join(
                            [
                                f"{msg}the Kubernetes context '{kubernetes_context}' configured for the ",
                                "Kubernetes deployer is not the same as the active context in the local ",
                                "Kubernetes configuration. If this is not deliberate, you should update the ",
                                "deployer's `kubernetes_context` field by running:\n\n",
                                f"  `zenml deployer update {self.name} --kubernetes_context={active_context}`\n",
                                "To list all configured contexts, run:\n\n",
                                "  `kubectl config get-contexts`\n",
                                "To set the active context to be the same as the one configured in the ",
                                "Kubernetes deployer and silence this warning, run:\n\n",
                                f"  `kubectl config use-context {kubernetes_context}`\n",
                            ]
                        )
                        logger.warning(warning_msg)
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
        deployment: DeploymentResponse,
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
    ) -> Dict[str, Any]:
        """Build template rendering context from deployment configuration.

        Args:
            deployment: The deployment response object.
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

        Returns:
            Template context dictionary.
        """
        resources = {}
        if resource_requests:
            resources["requests"] = resource_requests
        if resource_limits:
            resources["limits"] = resource_limits

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
                update={
                    "env": (settings.pod_settings.env or []) + secret_env_list
                }
            )
        elif secret_env_list:
            pod_settings_for_template = KubernetesPodSettings(
                env=secret_env_list
            )

        command = settings.command
        if not command:
            command = cast(
                Any,
                DeploymentEntrypointConfiguration.get_entrypoint_command(),
            )

        args = settings.args
        if not args:
            entrypoint_kwargs = {DEPLOYMENT_ID_OPTION: deployment.id}
            if deployment.snapshot:
                entrypoint_kwargs[SNAPSHOT_ID_OPTION] = deployment.snapshot.id
            args = cast(
                Any,
                DeploymentEntrypointConfiguration.get_entrypoint_arguments(
                    **entrypoint_kwargs
                ),
            )

        context = {
            "deployment": deployment,
            "settings": settings,
            "name": resource_name,
            "namespace": namespace,
            "labels": labels,
            "image": image,
            "command": command,
            "args": args,
            "env": env_vars,
            "resources": resources if resources else None,
            "pod_settings": pod_settings_for_template,
            "replicas": replicas,
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

    def _find_resources_to_delete(
        self,
        old_inventory: List[ResourceInventoryItem],
        new_inventory: List[ResourceInventoryItem],
    ) -> List[ResourceInventoryItem]:
        """Find resources in old inventory that are not in new inventory.

        Args:
            old_inventory: Resources from previous deployment.
            new_inventory: Resources from current deployment.

        Returns:
            List of resources that should be deleted.
        """
        new_resource_ids = {
            (item.kind, item.api_version, item.name, item.namespace)
            for item in new_inventory
        }

        resources_to_delete = []
        for item in old_inventory:
            resource_id = (
                item.kind,
                item.api_version,
                item.name,
                item.namespace,
            )
            if resource_id not in new_resource_ids:
                resources_to_delete.append(item)

        return resources_to_delete

    def _wait_for_deployment_readiness(
        self,
        inventory: List[ResourceInventoryItem],
        settings: KubernetesDeployerSettings,
        timeout: int,
    ) -> None:
        """Wait for all deployments and load balancer services to become ready.

        Uses the resource inventory to find all Deployment and LoadBalancer Service
        resources, then waits for each one to become ready.

        Args:
            inventory: List of provisioned resources to wait for.
            settings: Kubernetes deployer settings.
            timeout: Timeout in seconds.

        Raises:
            DeploymentProvisionError: If any deployment doesn't become ready in time.
        """
        if timeout <= 0:
            return

        deployments = [
            item
            for item in inventory
            if item.kind == "Deployment" and item.api_version == "apps/v1"
        ]

        for deployment_item in deployments:
            try:
                logger.info(
                    f"Waiting for Deployment '{deployment_item.name}' "
                    f"in namespace '{deployment_item.namespace}' to become ready "
                    f"(timeout: {timeout}s)"
                )
                if not deployment_item.namespace:
                    raise RuntimeError(
                        f"Deployment '{deployment_item.name}' has no namespace"
                    )
                self.k8s_applier.wait_for_deployment_ready(
                    name=deployment_item.name,
                    namespace=deployment_item.namespace,
                    timeout=timeout,
                    check_interval=settings.deployment_ready_check_interval,
                )
                logger.info(f"Deployment '{deployment_item.name}' is ready")
            except RuntimeError as e:
                raise DeploymentProvisionError(
                    f"Deployment '{deployment_item.name}' in namespace "
                    f"'{deployment_item.namespace}' did not become ready: {e}"
                ) from e

        if settings.wait_for_load_balancer_timeout > 0:
            services = [
                item
                for item in inventory
                if item.kind == "Service" and item.api_version == "v1"
            ]

            lb_timeout = min(
                timeout,
                settings.wait_for_load_balancer_timeout,
                MAX_LOAD_BALANCER_TIMEOUT,
            )

            for service_item in services:
                try:
                    service = self.k8s_applier.get_resource(
                        name=service_item.name,
                        namespace=service_item.namespace,
                        kind="Service",
                        api_version="v1",
                    )
                    if not service:
                        continue

                    service_type = (
                        normalize_resource_to_dict(service)
                        .get("spec", {})
                        .get("type")
                    )
                    if service_type != "LoadBalancer":
                        continue

                    logger.info(
                        f"Waiting for LoadBalancer Service '{service_item.name}' "
                        f"in namespace '{service_item.namespace}' to get external IP "
                        f"(timeout: {lb_timeout}s)"
                    )
                    if not service_item.namespace:
                        raise RuntimeError(
                            f"Service '{service_item.name}' has no namespace"
                        )
                    self.k8s_applier.wait_for_service_loadbalancer_ip(
                        name=service_item.name,
                        namespace=service_item.namespace,
                        timeout=lb_timeout,
                        check_interval=settings.deployment_ready_check_interval,
                    )
                    logger.info(
                        f"LoadBalancer Service '{service_item.name}' has external IP"
                    )
                except RuntimeError:
                    logger.warning(
                        f"LoadBalancer Service '{service_item.name}' did not get "
                        f"external IP within {lb_timeout}s.\n"
                        f"  This can happen if:\n"
                        f"  • You're on a local cluster (minikube, kind, k3d, docker-desktop) that doesn't support LoadBalancers\n"
                        f"  • Your cloud provider is slow to provision the load balancer\n"
                        f"  • There are cloud provider issues (quotas, permissions, etc.)\n"
                        f"\n"
                        f"  Next steps:\n"
                        f"  1. Check if IP appears: kubectl get svc {service_item.name} -n {service_item.namespace}\n"
                        f"  2. Refresh deployment status later to check if IP was assigned: zenml deployment refresh <deployment-name>\n"
                        f"  3. For local clusters, consider using service_type='NodePort' instead\n"
                        f"  4. For immediate access: kubectl port-forward -n {service_item.namespace} service/{service_item.name} <local-port>:<service-port>"
                    )
                except Exception as e:
                    logger.warning(
                        f"Error checking service '{service_item.name}': {e}"
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
            resource_requests, resource_limits, replicas = (
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
            deployment=deployment,
            settings=ctx.settings,
            resource_name=ctx.resource_name,
            namespace=ctx.namespace,
            labels=ctx.labels,
            image=ctx.image,
            env_vars=environment,
            secret_env_vars=validated_secrets,
            secret_name=ctx.secret_name,
            resource_requests=resource_requests,
            resource_limits=resource_limits,
            replicas=replicas,
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
                additional_docs = engine.render_template(
                    additional_resource, context
                )
                if additional_docs:
                    rendered_resources.extend(additional_docs)
                else:
                    logger.debug(
                        f"Additional resource '{additional_resource}' rendered "
                        f"to no documents (empty or all conditionals False)"
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
            stack: The stack the pipeline will be deployed on.
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

        stored_metadata = deployment.deployment_metadata or {}
        old_inventory_data = stored_metadata.get("resource_inventory")

        try:
            created_objects, new_inventory = self.k8s_applier.provision(
                rendered_resources,
                default_namespace=ctx.namespace,
                timeout=timeout,
            )
            logger.info(
                f"Successfully created/updated {len(created_objects)} "
                f"Kubernetes resource(s) for deployment '{deployment.name}'"
            )

            if old_inventory_data:
                old_inventory = [
                    ResourceInventoryItem(**item)
                    for item in old_inventory_data
                ]
                resources_to_delete = self._find_resources_to_delete(
                    old_inventory, new_inventory
                )
                if resources_to_delete:
                    logger.info(
                        f"Cleaning up {len(resources_to_delete)} obsolete "
                        f"resource(s) from previous deployment of "
                        f"'{deployment.name}'"
                    )
                    delete_result = self.k8s_applier.delete_from_inventory(
                        inventory=resources_to_delete,
                        propagation_policy="Foreground",
                    )
                    logger.info(
                        "Obsolete resource cleanup result: "
                        f"deleted={delete_result.deleted_count} "
                        f"skipped={delete_result.skipped_count} "
                        f"failed={delete_result.failed_count}"
                    )

            self._wait_for_deployment_readiness(
                inventory=new_inventory,
                settings=ctx.settings,
                timeout=timeout,
            )

            state = self._get_deployment_state_from_inventory(
                inventory=new_inventory,
                settings=ctx.settings,
            )

            if state.metadata is None:
                state.metadata = {}
            state.metadata["resource_inventory"] = [
                item.model_dump() for item in new_inventory
            ]

            return state

        except ProvisioningError as e:
            new_inventory = e.inventory
            for error_line in e.errors:
                logger.error(f"  • {error_line}")

            if ctx.settings.atomic_provision and new_inventory:
                logger.warning(
                    f"Atomic provision enabled – rolling back "
                    f"{len(new_inventory)} resource(s) for '{deployment.name}'"
                )
                delete_result = self.k8s_applier.delete_from_inventory(
                    inventory=new_inventory,
                    propagation_policy="Foreground",
                )
                raise DeploymentProvisionError(
                    "Kubernetes provisioning failed for deployment "
                    f"'{deployment.name}' with atomic_provision=True.\n"
                    f"Errors ({len(e.errors)}):\n"
                    + "\n".join(f"  • {err}" for err in e.errors)
                    + "\n\nRollback summary:\n"
                    f"  deleted={delete_result.deleted_count}, "
                    f"skipped={delete_result.skipped_count}, "
                    f"failed={delete_result.failed_count}"
                ) from e

            deployment_state = DeploymentOperationalState(
                status=DeploymentStatus.ERROR,
                metadata={
                    "namespace": ctx.namespace,
                    "labels": ctx.labels,
                    "resource_inventory": [
                        item.model_dump() for item in new_inventory
                    ],
                    "errors": e.errors,
                },
            )
            deployment = self._update_deployment(deployment, deployment_state)

            raise DeploymentProvisionError(
                f"Kubernetes provisioning failed for deployment "
                f"'{deployment.name}'. Errors:\n"
                + "\n".join(f"  • {err}" for err in e.errors)
            ) from e

        except Exception as e:
            raise DeploymentProvisionError(
                f"Failed to provision deployment '{deployment.name}': {e}"
            ) from e

    # ========================================================================
    # State Management
    # ========================================================================

    def _get_deployment_state_from_inventory(
        self,
        inventory: List[ResourceInventoryItem],
        settings: KubernetesDeployerSettings,
    ) -> DeploymentOperationalState:
        """Get deployment state from a resource inventory.

        This helper method extracts state determination logic so it can be
        used both during provisioning (when inventory is in memory) and when
        querying (when inventory comes from stored metadata).

        Args:
            inventory: The resource inventory to check.
            settings: The deployer settings.

        Returns:
            The operational state.

        Raises:
            DeploymentNotFoundError: If no deployment resources found in cluster.
            DeployerError: If an error occurs checking resources.
        """
        deployment_items = [
            item
            for item in inventory
            if item.kind == "Deployment" and item.api_version == "apps/v1"
        ]

        service_items = [
            item
            for item in inventory
            if item.kind == "Service" and item.api_version == "v1"
        ]

        try:
            status = DeploymentStatus.PENDING
            all_ready = True
            any_exists = False

            for deployment_item in deployment_items:
                k8s_deployment = self.k8s_applier.get_resource(
                    name=deployment_item.name,
                    namespace=deployment_item.namespace,
                    kind="Deployment",
                    api_version="apps/v1",
                )

                if not k8s_deployment:
                    logger.debug(
                        f"Deployment '{deployment_item.name}' not found in cluster"
                    )
                    all_ready = False
                    continue

                any_exists = True

                deployment_dict = normalize_resource_to_dict(k8s_deployment)
                status_data = deployment_dict.get("status", {})
                spec_data = deployment_dict.get("spec", {})
                available = status_data.get("availableReplicas", 0)
                desired = spec_data.get("replicas", 0)

                logger.debug(
                    f"Deployment '{deployment_item.name}': "
                    f"available={available}, desired={desired}"
                )

                if desired == 0:
                    logger.debug(
                        f"Deployment '{deployment_item.name}' is scaled to zero "
                        f"(idle-ready state)"
                    )
                elif available < desired:
                    all_ready = False

            if not any_exists:
                raise DeploymentNotFoundError(
                    "No deployment resources found in cluster"
                )

            if all_ready:
                status = DeploymentStatus.RUNNING

            url = None
            namespace = settings.namespace

            for service_item in service_items:
                k8s_service = self.k8s_applier.get_resource(
                    name=service_item.name,
                    namespace=service_item.namespace,
                    kind="Service",
                    api_version="v1",
                )

                if k8s_service:
                    service_url = kube_utils.build_service_url(
                        core_api=self.k8s_core_api,
                        service=k8s_service,
                        namespace=service_item.namespace or namespace,
                        ingress=None,
                    )
                    if service_url:
                        url = service_url
                        break

            metadata = {
                "namespace": namespace,
                "labels": settings.labels,
            }

            return DeploymentOperationalState(
                status=status,
                url=url,
                metadata=metadata,
            )

        except ApiException as e:
            if e.status == 404:
                raise DeploymentNotFoundError(
                    "Deployment resources not found in cluster"
                )
            raise DeployerError(f"Failed to get deployment state: {e}")

    def do_get_deployment_state(
        self, deployment: DeploymentResponse
    ) -> DeploymentOperationalState:
        """Get deployment state based on inventory.

        This method checks ALL resources in the inventory to determine status:
        - Checks all Deployment resources to see if they're ready
        - Checks all Service resources to get URLs
        - Works with both built-in and custom templates

        Args:
            deployment: The deployment.

        Returns:
            The operational state.

        Raises:
            DeploymentNotFoundError: If no resources found in cluster.
        """
        ctx = self._initialize_deployment_context(deployment)

        stored_metadata = deployment.deployment_metadata or {}
        inventory_data = stored_metadata.get("resource_inventory")

        if not inventory_data:
            raise DeploymentNotFoundError(
                f"Deployment '{deployment.name}' has no stored resource inventory"
            )

        inventory = [
            ResourceInventoryItem(**item)
            for item in stored_metadata["resource_inventory"]
        ]

        state = self._get_deployment_state_from_inventory(
            inventory=inventory,
            settings=ctx.settings,
        )

        if state.metadata is None:
            state.metadata = {}
        state.metadata["resource_inventory"] = stored_metadata[
            "resource_inventory"
        ]

        return state

    # ========================================================================
    # Logs
    # ========================================================================

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get deployment logs from all pods.

        Args:
            deployment: The deployment.
            follow: Whether to follow logs (only follows first pod if true).
            tail: Number of lines to tail per pod.

        Yields:
            Log lines from all pods, prefixed with pod name.

        Raises:
            DeploymentLogsNotFoundError: If no Deployment found or pods unavailable.
            DeployerError: If deployment has no inventory.
        """
        ctx = self._initialize_deployment_context(deployment)

        stored_metadata = deployment.deployment_metadata or {}
        inventory_data = stored_metadata.get("resource_inventory")

        if not inventory_data:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no resource inventory"
            )

        inventory = [ResourceInventoryItem(**item) for item in inventory_data]

        deployment_items = [
            item
            for item in inventory
            if item.kind == "Deployment" and item.api_version == "apps/v1"
        ]

        if not deployment_items:
            raise DeploymentLogsNotFoundError(
                f"No Deployment resources in inventory for '{deployment.name}'"
            )

        deployment_item = deployment_items[0]

        try:
            k8s_deployment_obj = self.k8s_applier.get_resource(
                name=deployment_item.name,
                namespace=deployment_item.namespace,
                kind="Deployment",
                api_version="apps/v1",
            )

            if not k8s_deployment_obj:
                raise DeploymentLogsNotFoundError(
                    f"Deployment '{deployment_item.name}' not found in cluster"
                )

            k8s_deployment = normalize_resource_to_dict(k8s_deployment_obj)
            label_selector: Dict[str, str] = {}
            try:
                spec = k8s_deployment.get("spec", {})
                selector = spec.get("selector", {})
                label_selector = (
                    selector.get("matchLabels")
                    or selector.get("match_labels")
                    or {}
                )
            except (AttributeError, TypeError):
                pass

            if not label_selector:
                raise DeploymentLogsNotFoundError(
                    f"Deployment '{deployment_item.name}' has no label selector"
                )

            label_selector_str = ",".join(
                f"{k}={v}" for k, v in label_selector.items()
            )

            pods = self.k8s_applier.list_resources(
                namespace=deployment_item.namespace or ctx.namespace,
                kind="Pod",
                api_version="v1",
                label_selector=label_selector_str,
            )

            if not pods:
                raise DeploymentLogsNotFoundError(
                    f"No pods found for Deployment '{deployment_item.name}'"
                )

            container_name = "main"
            try:
                spec = k8s_deployment.get("spec", {})
                template = spec.get("template", {})
                template_spec = template.get("spec", {})
                containers = template_spec.get("containers", [])
                if (
                    containers
                    and isinstance(containers, list)
                    and len(containers) > 0
                ):
                    container_name = containers[0].get("name", "main")
            except (AttributeError, TypeError, IndexError):
                pass

            if follow:
                pod_name = pods[0].metadata.name
                resp = self.k8s_core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=deployment_item.namespace or ctx.namespace,
                    container=container_name,
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
                for pod in pods:
                    pod_name = pod.metadata.name
                    try:
                        logs = self.k8s_core_api.read_namespaced_pod_log(
                            name=pod_name,
                            namespace=deployment_item.namespace
                            or ctx.namespace,
                            container=container_name,
                            tail_lines=tail,
                        )
                        for line in logs.split("\n"):
                            if line:
                                yield f"[{pod_name}] {line}"
                    except ApiException as pod_err:
                        logger.warning(
                            f"Failed to get logs from pod '{pod_name}': {pod_err}"
                        )
                        continue

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
            DeploymentNotFoundError: If deployment has no inventory.
        """
        stored_metadata = deployment.deployment_metadata
        inventory_data = stored_metadata.get("resource_inventory")

        if not inventory_data:
            logger.info(
                f"No inventory found for deployment '{deployment.name}'. "
                f"Treating as already deprovisioned."
            )
            raise DeploymentNotFoundError(
                f"No resource inventory stored for deployment '{deployment.name}'"
            )

        inventory = [ResourceInventoryItem(**item) for item in inventory_data]
        logger.info(
            f"Deprovisioning deployment '{deployment.name}' "
            f"({len(inventory)} resource(s) in inventory)"
        )

        try:
            result = self.k8s_applier.delete_from_inventory(
                inventory=inventory,
                propagation_policy="Foreground",
            )

            if result.deleted_count == 0 and result.failed_count == 0:
                logger.info(
                    f"All resources for deployment '{deployment.name}' "
                    f"were already deleted or skipped"
                )
                return None

            if result.failed_count == 0:
                logger.info(
                    f"Successfully deprovisioned deployment '{deployment.name}' "
                    f"({result.deleted_count} deleted, {result.skipped_count} skipped)"
                )
                return None

            failed_list = "\n".join(
                f"  ❌ {r}" for r in result.failed_resources
            )

            error_msg = (
                f"Partial deprovisioning failure for deployment '{deployment.name}':\n"
                f"  ✅ Deleted: {result.deleted_count} resource(s)\n"
                f"  ⏭️  Skipped: {result.skipped_count} resource(s)\n"
                f"  ❌ Failed: {result.failed_count} resource(s)\n\n"
                f"Resources that failed to delete:\n{failed_list}\n\n"
                f"The deployment will NOT be removed from ZenML to allow retry or manual cleanup.\n"
                f"You can retry deletion with: zenml deployment delete {deployment.name}"
            )
            logger.error(error_msg)
            raise DeploymentDeprovisionError(error_msg)

        except DeploymentDeprovisionError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error while deprovisioning '{deployment.name}': {e}. "
                f"Some resources may still exist. Manual cleanup may be required."
            )
            raise DeploymentDeprovisionError(
                f"Failed to deprovision deployment '{deployment.name}': {e}"
            ) from e
