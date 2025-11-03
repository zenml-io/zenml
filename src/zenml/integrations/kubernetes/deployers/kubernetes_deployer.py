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
    Optional,
    Tuple,
    Type,
    cast,
)

import yaml
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

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
    build_secret_manifest,
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


class KubernetesDeployer(ContainerizedDeployer):
    """Kubernetes deployer using template-based resource management."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Kubernetes deployer.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init__(**kwargs)

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
    def k8s_apps_api(self) -> k8s_client.AppsV1Api:
        """Get Kubernetes Apps V1 API client.

        Returns:
            Kubernetes Apps V1 API client.
        """
        return k8s_client.AppsV1Api(self.get_kube_client())

    @property
    def k8s_rbac_api(self) -> k8s_client.RbacAuthorizationV1Api:
        """Get Kubernetes RBAC API client.

        Returns:
            Kubernetes RBAC API client.
        """
        return k8s_client.RbacAuthorizationV1Api(self.get_kube_client())

    @property
    def k8s_networking_api(self) -> k8s_client.NetworkingV1Api:
        """Get Kubernetes Networking API client.

        Returns:
            Kubernetes Networking API client.
        """
        return k8s_client.NetworkingV1Api(self.get_kube_client())

    @property
    def k8s_autoscaling_api(self) -> k8s_client.AutoscalingV2Api:
        """Get Kubernetes Autoscaling API client.

        Returns:
            Kubernetes Autoscaling API client.
        """
        return k8s_client.AutoscalingV2Api(self.get_kube_client())

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
    # Resource Naming
    # ========================================================================

    def _get_namespace(self, deployment: DeploymentResponse) -> str:
        """Get namespace for deployment.

        Args:
            deployment: The deployment to get namespace for.

        Returns:
            The namespace name.

        Raises:
            DeployerError: If deployment has no snapshot.
        """
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no snapshot"
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )
        return settings.namespace or self.config.kubernetes_namespace

    def _get_resource_name(self, deployment: DeploymentResponse) -> str:
        """Get resource name for deployment.

        Args:
            deployment: The deployment to get resource name for.

        Returns:
            Sanitized resource name.
        """
        name = f"zenml-{deployment.id}"
        return kube_utils.sanitize_label(name)[:MAX_K8S_NAME_LENGTH]

    def _get_labels(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
    ) -> Dict[str, str]:
        """Get labels for Kubernetes resources.

        Args:
            deployment: The deployment to create labels for.
            settings: Deployer settings.

        Returns:
            Dictionary of sanitized labels.
        """
        labels = {
            "zenml-deployment-id": str(deployment.id),
            "zenml-deployment-name": kube_utils.sanitize_label(
                deployment.name
            ),
            "managed-by": "zenml",
        }
        if settings.labels:
            labels.update(settings.labels)
        return labels

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

        pod_settings_dict = (
            settings.pod_settings.model_dump() if settings.pod_settings else {}
        )

        if secret_env_list:
            existing_env = pod_settings_dict.get("env", [])
            if not isinstance(existing_env, list):
                existing_env = []
            pod_settings_dict["env"] = existing_env + secret_env_list

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
            "security_context": (
                pod_settings_dict.get("security_context")
                if pod_settings_dict
                else None
            ),
            "service_type": settings.service_type,
            "service_port": settings.service_port,
            "target_port": settings.service_port,
            "pod_settings": pod_settings_dict,
        }

        return context

    # ========================================================================
    # Secret Management
    # ========================================================================

    def _cleanup_deployment_resources(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        resource_name: str,
        applier: KubernetesApplier,
    ) -> None:
        """Clean up partially created deployment resources.

        This is called when provisioning fails to remove any resources
        that were created before the failure occurred.

        Args:
            deployment: The deployment response.
            namespace: Kubernetes namespace.
            resource_name: Name of the resources.
            applier: KubernetesApplier instance.
        """
        logger.warning(
            f"[Deployment {deployment.name}] Cleaning up partially created resources "
            f"(namespace: {namespace}, resource: {resource_name})"
        )
        cleanup_errors = []

        try:
            applier.delete_resource(
                name=resource_name,
                namespace=namespace,
                kind="Service",
                api_version="v1",
            )
            logger.debug(f"Deleted Service: {resource_name}")
        except ApiException as e:
            if e.status != 404:
                cleanup_errors.append(f"Service: {e}")

        try:
            applier.delete_resource(
                name=resource_name,
                namespace=namespace,
                kind="Deployment",
                api_version="apps/v1",
            )
            logger.debug(f"Deleted Deployment: {resource_name}")
        except ApiException as e:
            if e.status != 404:
                cleanup_errors.append(f"Deployment: {e}")

        secret_name = f"zenml-{deployment.id}"
        try:
            applier.delete_resource(
                name=secret_name,
                namespace=namespace,
                kind="Secret",
                api_version="v1",
            )
            logger.debug(f"Deleted Secret: {secret_name}")
        except ApiException as e:
            if e.status != 404:
                cleanup_errors.append(f"Secret: {e}")

        if cleanup_errors:
            logger.warning(
                f"Some resources could not be cleaned up: {', '.join(cleanup_errors)}"
            )
        else:
            logger.info(
                f"Successfully cleaned up resources for '{deployment.name}'"
            )

    def _sanitize_secret_key(
        self, key: str, secret_key_map: Dict[str, str]
    ) -> str:
        """Sanitize secret key to valid K8s env var name and detect collisions.

        Args:
            key: Original secret key name.
            secret_key_map: Dictionary tracking sanitized key mappings to detect collisions.

        Returns:
            Sanitized secret key name.

        Raises:
            DeploymentProvisionError: If sanitization causes a collision with an existing key.
        """
        original = key
        sanitized = re.sub(r"[^A-Za-z0-9_]", "_", key)
        if not sanitized or not re.match(r"^[A-Za-z_]", sanitized):
            sanitized = f"_{sanitized}" if sanitized else "_VAR"
        if sanitized in secret_key_map:
            if secret_key_map[sanitized] != original:
                raise DeploymentProvisionError(
                    f"Secret key collision: '{original}' and '{secret_key_map[sanitized]}' "
                    f"both sanitize to '{sanitized}'. Please rename one of them."
                )
        else:
            secret_key_map[sanitized] = original

        return sanitized

    def _prepare_secrets(
        self,
        deployment: DeploymentResponse,
        namespace: str,
        secrets: Dict[str, str],
        applier: KubernetesApplier,
    ) -> Dict[str, str]:
        """Sanitize and create Kubernetes secret.

        Args:
            deployment: The deployment response.
            namespace: Kubernetes namespace.
            secrets: Secret environment variables.
            applier: KubernetesApplier instance.

        Returns:
            Sanitized secrets dict.
        """
        if not secrets:
            return {}

        secret_key_map: Dict[str, str] = {}
        sanitized = {}
        for key, value in secrets.items():
            sanitized_key = self._sanitize_secret_key(key, secret_key_map)
            if sanitized_key != key:
                logger.warning(
                    f"Secret key '{key}' sanitized to '{sanitized_key}'"
                )
            sanitized[sanitized_key] = value

        secret_name = f"zenml-{deployment.id}"
        secret_manifest = build_secret_manifest(
            name=secret_name,
            data=cast(Dict[str, Optional[str]], sanitized),
        )
        secret_manifest.metadata.namespace = namespace

        applier.apply_resource(resource=secret_manifest, dry_run=False)
        return sanitized

    # ========================================================================
    # Provisioning
    # ========================================================================

    def _validate_and_prepare_deployment(
        self,
        deployment: DeploymentResponse,
    ) -> Tuple[KubernetesDeployerSettings, str, str, Dict[str, str], str]:
        """Validate deployment and prepare basic settings.

        Args:
            deployment: The deployment response.

        Returns:
            Tuple of (settings, namespace, resource_name, labels, image).

        Raises:
            DeploymentProvisionError: If validation fails.
        """
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeploymentProvisionError(
                f"Deployment '{deployment.name}' has no snapshot"
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )

        namespace = self._get_namespace(deployment)
        resource_name = self._get_resource_name(deployment)
        labels = self._get_labels(deployment, settings)
        image = self.get_image(snapshot)

        return settings, namespace, resource_name, labels, image

    def _validate_additional_resources(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
        context: Dict[str, Any],
        applier: KubernetesApplier,
        engine: KubernetesTemplateEngine,
    ) -> None:
        """Validate additional resources before provisioning.

        Validates that:
        1. Additional resource files can be loaded
        2. Resources have valid schema (kind, apiVersion)
        3. Resources can be validated with Kubernetes API (dry-run)

        Args:
            deployment: The deployment response.
            settings: Kubernetes deployer settings.
            context: Template rendering context.
            applier: KubernetesApplier instance.
            engine: Template engine instance.

        Raises:
            DeploymentProvisionError: If validation fails.
        """
        if not settings.additional_resources:
            return

        try:
            loaded_resources = engine.load_additional_resources(
                settings.additional_resources,
                context=context,
            )
        except ValueError as e:
            raise DeploymentProvisionError(
                f"Failed to load additional resources for validation: {e}"
            ) from e

        for resource_dict in loaded_resources:
            kind = resource_dict.get("kind")
            api_version = resource_dict.get("apiVersion")
            metadata = resource_dict.get("metadata", {})
            name = metadata.get("name", "unnamed")

            if not kind or not api_version:
                raise DeploymentProvisionError(
                    f"Invalid additional resource '{name}': missing 'kind' or 'apiVersion'"
                )

            try:
                applier.ssa_apply(
                    resource=resource_dict, dry_run=True, force=True
                )
                logger.debug(
                    f"[Deployment {deployment.name}] Validated additional resource: {kind}/{name}"
                )
            except ApiException as e:
                # 409 Conflict during dry-run means resource exists with different field manager
                # This is acceptable - actual deployment will use force=True to take ownership
                if e.status == 409:
                    logger.debug(
                        f"[Deployment {deployment.name}] Resource {kind}/{name} exists with different field manager - will be updated during deployment"
                    )
                else:
                    raise DeploymentProvisionError(
                        f"Invalid additional resource {kind}/{name}: {e.reason}"
                    ) from e
            except ValueError as e:
                raise DeploymentProvisionError(
                    f"Invalid additional resource {kind}/{name}: {e}"
                ) from e

    def _prepare_namespace(
        self,
        namespace: str,
        applier: KubernetesApplier,
        dry_run: bool,
    ) -> None:
        """Ensure namespace exists.

        Args:
            namespace: Kubernetes namespace name.
            applier: KubernetesApplier instance.
            dry_run: If True, skip namespace creation.

        Raises:
            DeploymentProvisionError: If namespace creation fails.
        """
        if dry_run:
            return

        try:
            namespace_manifest = {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": namespace},
            }
            applier.apply_resource(resource=namespace_manifest, dry_run=False)
        except ApiException as e:
            raise DeploymentProvisionError(
                f"Failed to create namespace '{namespace}': {e}"
            ) from e

    def _render_k8s_resources(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
        context: Dict[str, Any],
        engine: Optional[KubernetesTemplateEngine] = None,
    ) -> Tuple[
        Dict[str, Any], str, Dict[str, Any], str, KubernetesTemplateEngine
    ]:
        """Render Kubernetes deployment and service templates.

        Args:
            deployment: The deployment response.
            settings: Kubernetes deployer settings.
            context: Template rendering context.
            engine: Optional pre-initialized template engine. If None, creates one.

        Returns:
            Tuple of (deployment dict, deployment canonical YAML,
            service dict, service canonical YAML, template engine).

        Raises:
            DeploymentProvisionError: If template rendering fails.
        """
        if engine is None:
            engine = KubernetesTemplateEngine(
                custom_templates_dir=settings.custom_templates_dir
            )

        try:
            deployment_manifest = engine.render_to_k8s_object(
                template_name="deployment.yaml.j2",
                context=context,
            )
            service_manifest = engine.render_to_k8s_object(
                template_name="service.yaml.j2",
                context=context,
            )
        except Exception as e:
            raise DeploymentProvisionError(
                f"Failed to render Kubernetes templates for '{deployment.name}': {e}"
            ) from e

        if settings.save_manifests:
            manifests = {
                "deployment.yaml": deployment_manifest.canonical_yaml,
                "service.yaml": service_manifest.canonical_yaml,
            }

            if settings.additional_resources:
                try:
                    loaded_resources = engine.load_additional_resources(
                        settings.additional_resources,
                        context=context,
                    )
                    for idx, resource_dict in enumerate(loaded_resources, 1):
                        kind = resource_dict.get("kind", "Unknown").lower()
                        name = resource_dict.get("metadata", {}).get(
                            "name", "unnamed"
                        )
                        filename = f"additional-{idx:02d}-{kind}-{name}.yaml"
                        manifests[filename] = yaml.dump(
                            resource_dict,
                            default_flow_style=False,
                            sort_keys=False,
                        )
                except ValueError as e:
                    logger.warning(
                        f"Could not load additional resources for saving: {e}"
                    )
                except Exception as e:
                    logger.warning(f"Could not save additional resources: {e}")

            save_dir = engine.save_manifests(
                manifests=manifests,
                deployment_name=context["name"],
                output_dir=settings.manifest_output_dir,
            )
            logger.info(
                f"[Deployment {deployment.name}] Saved {len(manifests)} manifests to: {save_dir}"
            )

        if settings.print_manifests:
            logger.info("=" * 80)
            logger.info("KUBERNETES DEPLOYMENT MANIFEST")
            logger.info("=" * 80)
            logger.info(deployment_manifest.canonical_yaml)
            logger.info("=" * 80)
            logger.info("KUBERNETES SERVICE MANIFEST")
            logger.info("=" * 80)
            logger.info(service_manifest.canonical_yaml)
            logger.info("=" * 80)

            if settings.additional_resources:
                try:
                    loaded_resources = engine.load_additional_resources(
                        settings.additional_resources,
                        context=context,
                    )
                    for idx, resource_dict in enumerate(loaded_resources, 1):
                        kind = resource_dict.get("kind", "Unknown")
                        name = resource_dict.get("metadata", {}).get(
                            "name", "unnamed"
                        )
                        logger.info(
                            f"ADDITIONAL RESOURCE #{idx}: {kind.upper()} ({name})"
                        )
                        logger.info("=" * 80)
                        resource_yaml = yaml.dump(
                            resource_dict,
                            default_flow_style=False,
                            sort_keys=False,
                        )
                        logger.info(resource_yaml)
                        logger.info("=" * 80)
                except ValueError as e:
                    logger.warning(
                        f"Could not load additional resources for printing: {e}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not print additional resources: {e}"
                    )

        return (
            deployment_manifest.resource_dict,
            deployment_manifest.canonical_yaml,
            service_manifest.resource_dict,
            service_manifest.canonical_yaml,
            engine,
        )

    def _apply_core_resources(
        self,
        deployment: DeploymentResponse,
        k8s_deployment: Dict[str, Any],
        k8s_service: Dict[str, Any],
        applier: KubernetesApplier,
        resource_name: str,
        namespace: str,
        dry_run: bool,
    ) -> None:
        """Apply core Kubernetes resources (Deployment and Service).

        Args:
            deployment: The deployment response.
            k8s_deployment: Kubernetes Deployment dict.
            k8s_service: Kubernetes Service dict.
            applier: KubernetesApplier instance.
            resource_name: Resource name.
            namespace: Kubernetes namespace.
            dry_run: If True, only validate resources.

        Raises:
            DeploymentProvisionError: If applying resources fails.
        """
        if dry_run:
            logger.debug(f"   🔹 Validating Deployment: {resource_name}")
            try:
                applier.apply_resource(resource=k8s_deployment, dry_run=True)
                logger.debug(f"   🔹 Validating Service: {resource_name}")
                applier.apply_resource(resource=k8s_service, dry_run=True)
                logger.debug("   ✅ Core resources validated")
            except (ValueError, ApiException) as e:
                raise DeploymentProvisionError(
                    f"❌ Validation failed for '{deployment.name}': {e}"
                ) from e
            return

        try:
            applier.apply_resource(resource=k8s_deployment, dry_run=False)
            applier.apply_resource(resource=k8s_service, dry_run=False)
        except ApiException as e:
            self._cleanup_deployment_resources(
                deployment, namespace, resource_name, applier
            )
            raise DeploymentProvisionError(
                f"Failed to apply Kubernetes resources for '{deployment.name}': {e.reason}"
            ) from e

    def _apply_additional_resources(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
        namespace: str,
        applier: KubernetesApplier,
        context: Dict[str, Any],
        engine: KubernetesTemplateEngine,
    ) -> None:
        """Apply additional Kubernetes resources.

        Args:
            deployment: The deployment response.
            settings: Kubernetes deployer settings.
            namespace: Kubernetes namespace.
            applier: KubernetesApplier instance.
            context: Jinja2 template context for variable substitution.
            engine: Template engine instance to reuse.

        Raises:
            DeploymentProvisionError: If loading additional resources fails,
                or if strict_additional_resources=True and any resource fails to apply.
        """
        if not settings.additional_resources:
            return

        try:
            loaded_resources = engine.load_additional_resources(
                settings.additional_resources,
                context=context,
            )
        except ValueError as e:
            raise DeploymentProvisionError(
                f"Failed to load additional resources for deployment '{deployment.name}': {e}"
            ) from e

        strict = settings.strict_additional_resources

        for resource_dict in loaded_resources:
            kind = resource_dict.get("kind", "Unknown")
            metadata = resource_dict.get("metadata", {})
            name = metadata.get("name", "unnamed")

            try:
                applier.ensure_namespace_alignment(
                    resource_dict=resource_dict,
                    namespace=namespace,
                    deployment_name=deployment.name,
                )

                logger.info(f"📦 Applying additional resource: {kind}/{name}")

                applier.apply_resource(resource=resource_dict, dry_run=False)
                logger.debug(f"   ✅ Applied: {kind}/{name}")
            except Exception as e:
                if strict:
                    raise DeploymentProvisionError(
                        f"Failed to apply additional resource {kind}/{name}: {e}"
                    ) from e
                else:
                    logger.warning(
                        f"[Deployment {deployment.name}] Failed to apply {kind} '{name}': {e}. "
                        "Continuing with deployment..."
                    )

    def _wait_for_deployment_readiness(
        self,
        deployment: DeploymentResponse,
        settings: KubernetesDeployerSettings,
        resource_name: str,
        namespace: str,
        applier: KubernetesApplier,
        timeout: int,
    ) -> None:
        """Wait for deployment and service to become ready.

        Args:
            deployment: The deployment response.
            settings: Kubernetes deployer settings.
            resource_name: Resource name.
            namespace: Kubernetes namespace.
            applier: KubernetesApplier instance.
            timeout: Timeout in seconds.

        Raises:
            DeploymentProvisionError: If deployment doesn't become ready in time.
        """
        if timeout <= 0:
            return

        try:
            logger.info(
                f"\n⏳ Waiting for deployment to become ready...\n"
                f"   📋 Deployment: {deployment.name}\n"
                f"   📦 Namespace: {namespace}\n"
                f"   ⏱️  Timeout: {timeout}s"
            )
            applier.wait_for_deployment_ready(
                name=resource_name,
                namespace=namespace,
                timeout=timeout,
                check_interval=settings.deployment_ready_check_interval,
            )
            logger.info("✅ Deployment is ready!")
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
                    f"⏳ Waiting for LoadBalancer IP (timeout: {lb_timeout}s)..."
                )
                applier.wait_for_service_loadbalancer_ip(
                    name=resource_name,
                    namespace=namespace,
                    timeout=lb_timeout,
                    check_interval=settings.deployment_ready_check_interval,
                )
                logger.info("✅ LoadBalancer IP assigned")
            except RuntimeError:
                logger.warning(
                    f"⚠️  LoadBalancer IP not assigned within {lb_timeout}s\n"
                    f"   Service may still be accessible via cluster IP."
                )

    # ========================================================================
    # Provisioning
    # ========================================================================

    def do_dry_run_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> None:
        """Perform dry-run: build image, generate manifests, validate - but don't deploy.

        This method does EVERYTHING a real deployment would do EXCEPT actually
        deploying to Kubernetes:
        - Builds and pushes Docker images
        - Generates Kubernetes manifests
        - Saves manifests to .zenml-deployments/
        - Validates manifests with Kubernetes API
        - Prints manifests if requested

        Args:
            deployment: The deployment to validate (temporary, not in DB).
            stack: The stack to use.
            environment: Environment variables.
            secrets: Secret environment variables.
        """
        logger.info(
            f"\n{'=' * 70}\n"
            f"🧪 DRY-RUN MODE: Building & validating '{deployment.name}'\n"
            f"{'=' * 70}"
        )

        (
            settings,
            namespace,
            resource_name,
            labels,
            image,
            applier,
            k8s_deployment,
            k8s_service,
            context,
            engine,
        ) = self._prepare_deployment_resources(
            deployment, environment, secrets, skip_secrets=True
        )

        logger.info(f"✅ Image built and pushed:\n   └─ {image}")
        logger.info("✅ Manifests generated and saved to .zenml-deployments/")

        logger.info("\n🔍 Validating manifests with Kubernetes API...")
        self._validate_manifests_dry_run(
            deployment,
            k8s_deployment,
            k8s_service,
            applier,
            resource_name,
            namespace,
        )

        logger.info(
            f"\n{'=' * 70}\n"
            f"✅ DRY-RUN SUCCESSFUL!\n"
            f"{'=' * 70}\n"
            f"📋 Namespace: {namespace}\n"
            f"📦 Deployment: {resource_name}\n"
            f"💾 Manifests: .zenml-deployments/\n"
            f"\n💡 To deploy for real: Remove --dry-run flag\n"
            f"{'=' * 70}"
        )

    def _prepare_deployment_resources(
        self,
        deployment: DeploymentResponse,
        environment: Dict[str, str],
        secrets: Dict[str, str],
        skip_secrets: bool = False,
    ) -> Tuple[
        KubernetesDeployerSettings,
        str,
        str,
        Dict[str, str],
        str,
        KubernetesApplier,
        Dict[str, Any],
        Dict[str, Any],
        Dict[str, Any],
        KubernetesTemplateEngine,
    ]:
        """Prepare all resources needed for deployment (used by both dry-run and normal provisioning).

        Args:
            deployment: The deployment to prepare.
            environment: Environment variables.
            secrets: Secret environment variables.
            skip_secrets: If True, skip creating secrets.

        Returns:
            Tuple of (settings, namespace, resource_name, labels, image, applier,
                     k8s_deployment_dict, k8s_service_dict, context, engine)

        Raises:
            DeploymentProvisionError: If preparation fails.
        """
        settings, namespace, resource_name, labels, image = (
            self._validate_and_prepare_deployment(deployment)
        )

        snapshot = deployment.snapshot
        if not snapshot:
            raise DeploymentProvisionError(
                f"Deployment '{deployment.name}' has no snapshot"
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

        secret_name = f"zenml-{deployment.id}"
        applier = KubernetesApplier(api_client=self.get_kube_client())

        self._prepare_namespace(namespace, applier, skip_secrets)

        sanitized_secrets = {}
        if secrets and not skip_secrets:
            try:
                sanitized_secrets = self._prepare_secrets(
                    deployment, namespace, secrets, applier
                )
            except ApiException as e:
                raise DeploymentProvisionError(
                    f"Failed to create secrets for deployment '{deployment.name}': {e}"
                ) from e

        context = self._build_template_context(
            settings=settings,
            resource_name=resource_name,
            namespace=namespace,
            labels=labels,
            image=image,
            env_vars=environment,
            secret_env_vars=sanitized_secrets,
            secret_name=secret_name,
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

        k8s_deployment, _, k8s_service, _, engine = self._render_k8s_resources(
            deployment, settings, context
        )

        if not skip_secrets:
            self._validate_additional_resources(
                deployment, settings, context, applier, engine
            )

        return (
            settings,
            namespace,
            resource_name,
            labels,
            image,
            applier,
            k8s_deployment,
            k8s_service,
            context,
            engine,
        )

    def _validate_manifests_dry_run(
        self,
        deployment: DeploymentResponse,
        k8s_deployment: Dict[str, Any],
        k8s_service: Dict[str, Any],
        applier: KubernetesApplier,
        resource_name: str,
        namespace: str,
    ) -> None:
        """Validate Kubernetes manifests using dry-run API call.

        Args:
            deployment: The deployment.
            k8s_deployment: Kubernetes deployment dict.
            k8s_service: Kubernetes service dict.
            applier: KubernetesApplier instance.
            resource_name: Resource name.
            namespace: Kubernetes namespace.
        """
        logger.info(f"   🔸 Validating deployment '{deployment.name}'...")
        self._apply_core_resources(
            deployment,
            k8s_deployment,
            k8s_service,
            applier,
            resource_name,
            namespace,
            dry_run=True,
        )
        logger.info("   ✅ Validation successful")

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
        try:
            (
                settings,
                namespace,
                resource_name,
                labels,
                image,
                applier,
                k8s_deployment,
                k8s_service,
                context,
                engine,
            ) = self._prepare_deployment_resources(
                deployment, environment, secrets
            )

            self._apply_core_resources(
                deployment,
                k8s_deployment,
                k8s_service,
                applier,
                resource_name,
                namespace,
                dry_run=False,
            )

            self._apply_additional_resources(
                deployment, settings, namespace, applier, context, engine
            )

            self._wait_for_deployment_readiness(
                deployment,
                settings,
                resource_name,
                namespace,
                applier,
                timeout,
            )

            return self.do_get_deployment_state(deployment)

        except DeploymentProvisionError:
            raise
        except ApiException as e:
            if (
                "namespace" in locals()
                and "resource_name" in locals()
                and "applier" in locals()
            ):
                self._cleanup_deployment_resources(
                    deployment, namespace, resource_name, applier
                )
            raise DeploymentProvisionError(
                f"Kubernetes API error while provisioning '{deployment.name}': "
                f"{e.status} - {e.reason}"
            ) from e
        except Exception as e:
            if (
                "namespace" in locals()
                and "resource_name" in locals()
                and "applier" in locals()
            ):
                self._cleanup_deployment_resources(
                    deployment, namespace, resource_name, applier
                )
            raise DeploymentProvisionError(
                f"Unexpected error provisioning deployment '{deployment.name}': {e}"
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
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeployerError(
                f"Deployment '{deployment.name}' has no snapshot"
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )
        namespace = self._get_namespace(deployment)
        resource_name = self._get_resource_name(deployment)
        labels = self._get_labels(deployment, settings)

        applier = KubernetesApplier(api_client=self.get_kube_client())

        try:
            k8s_deployment = applier.get_resource(
                name=resource_name,
                namespace=namespace,
                kind="Deployment",
                api_version="apps/v1",
            )
            k8s_service = applier.get_resource(
                name=resource_name,
                namespace=namespace,
                kind="Service",
                api_version="v1",
            )

            if not k8s_deployment or not k8s_service:
                raise DeploymentNotFoundError(
                    f"Deployment '{deployment.name}' not found"
                )

            status = DeploymentStatus.PENDING
            # Convert ResourceField to dict for reliable access
            if hasattr(k8s_deployment, "to_dict"):
                deployment_dict = k8s_deployment.to_dict()
                status_data = deployment_dict.get("status", {})
                spec_data = deployment_dict.get("spec", {})
                available = status_data.get("availableReplicas", 0)
                desired = spec_data.get("replicas", 0)
            else:
                # Fallback to attribute access
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
                namespace=namespace,
                ingress=None,
            )

            metadata = {
                "deployment_name": resource_name,
                "namespace": namespace,
                "service_name": resource_name,
                "port": settings.service_port,
                "service_type": settings.service_type,
                "labels": labels,
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
        namespace = self._get_namespace(deployment)
        label_selector = f"zenml-deployment-id={deployment.id}"

        applier = KubernetesApplier(api_client=self.get_kube_client())

        try:
            pods = applier.list_resources(
                namespace=namespace,
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
                    namespace=namespace,
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
                    namespace=namespace,
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

        Args:
            deployment: The deployment to deprovision.
            timeout: Timeout in seconds.

        Returns:
            None to indicate immediate deletion.

        Raises:
            DeploymentDeprovisionError: If deprovisioning fails.
            DeploymentNotFoundError: If deployment not found.
        """
        snapshot = deployment.snapshot
        if not snapshot:
            raise DeploymentDeprovisionError(
                f"Deployment '{deployment.name}' has no snapshot"
            )

        settings = cast(
            KubernetesDeployerSettings,
            self.get_settings(snapshot),
        )
        namespace = self._get_namespace(deployment)
        resource_name = self._get_resource_name(deployment)

        try:
            applier = KubernetesApplier(api_client=self.get_kube_client())

            if settings.additional_resources:
                try:
                    engine = KubernetesTemplateEngine(
                        custom_templates_dir=settings.custom_templates_dir
                    )
                    loaded_resources = engine.load_additional_resources(
                        settings.additional_resources,
                        context=None,
                    )
                except ValueError as e:
                    logger.warning(
                        f"Failed to load additional resources for deletion: {e}. "
                        "Continuing with deletion of core resources..."
                    )
                    loaded_resources = []
                except Exception as e:
                    logger.warning(
                        f"Failed to load additional resources for deletion: {e}. "
                        "Continuing with deletion of core resources..."
                    )
                    loaded_resources = []

                for resource_dict in reversed(loaded_resources):
                    try:
                        kind = resource_dict.get("kind", "Unknown")
                        api_version = resource_dict.get("apiVersion", "v1")
                        name = resource_dict.get("metadata", {}).get(
                            "name", resource_name
                        )

                        logger.info(
                            f"Deleting additional resource: {kind}/{name}"
                        )
                        applier.delete_resource(
                            kind=kind,
                            name=name,
                            namespace=namespace,
                            api_version=api_version,
                        )
                    except ApiException as e:
                        if e.status != 404:
                            logger.warning(
                                f"Failed to delete {kind} '{name}': {e}"
                            )

            try:
                applier.delete_resource(
                    name=resource_name,
                    namespace=namespace,
                    kind="Service",
                    api_version="v1",
                )
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete Service: {e}")
            try:
                applier.delete_resource(
                    name=resource_name,
                    namespace=namespace,
                    kind="Deployment",
                    api_version="apps/v1",
                )
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete Deployment: {e}")

            secret_name = f"zenml-{deployment.id}"
            try:
                applier.delete_resource(
                    name=secret_name,
                    namespace=namespace,
                    kind="Secret",
                    api_version="v1",
                )
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete secret: {e}")

            logger.info(f"Deprovisioned deployment '{deployment.name}'")
            return None

        except DeploymentNotFoundError:
            raise
        except ApiException as e:
            if e.status == 404:
                raise DeploymentNotFoundError(
                    f"Deployment '{deployment.name}' not found"
                ) from e
            raise DeploymentDeprovisionError(
                f"Kubernetes API error while deprovisioning '{deployment.name}': "
                f"{e.status} - {e.reason}"
            ) from e
        except Exception as e:
            raise DeploymentDeprovisionError(
                f"Unexpected error deprovisioning '{deployment.name}': {e}"
            ) from e
