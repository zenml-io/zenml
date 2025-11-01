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
"""Kubernetes deployer flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import Field, PositiveInt, field_validator

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.enums import KubernetesServiceType
from zenml.integrations.kubernetes import KUBERNETES_DEPLOYER_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.deployers import KubernetesDeployer


class KubernetesDeployerSettings(BaseDeployerSettings):
    """Settings for the Kubernetes deployer.

    Follows a progressive complexity model:
    - Essential Settings: Core configuration for Deployment + Service (80% of users)
    - Additional Resources: Add ANY K8s resource (Ingress, HPA, NetworkPolicy, etc.)
    - Custom Templates: Override deployment.yaml.j2 or service.yaml.j2 for advanced control

    Essential Settings:
        namespace: Kubernetes namespace for deployments.
        service_type: How to expose service (LoadBalancer, NodePort, ClusterIP).
        service_port: Port to expose on the service.
        image_pull_policy: When to pull images (Always, IfNotPresent, Never).
        labels: Custom labels to apply to all resources.
        command: Override container command/entrypoint.
        args: Override container args.
        service_account_name: ServiceAccount for pods (RBAC).
        image_pull_secrets: Secrets for private registries.

    Advanced Settings:
        pod_settings: Advanced pod configuration (volumes, affinity, tolerations, etc.).
        additional_resources: List of complete K8s resource manifests as dicts or file paths.
        custom_templates_dir: Path to custom Jinja2 templates for Deployment/Service.
          Use this to customize health probes, service annotations, etc.

    Development/Testing:
        dry_run: Validate without creating resources.
        save_manifests: Save generated manifests to disk.
        manifest_output_dir: Custom directory for saved manifests.
    """

    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace for deployments. "
        "If not provided, uses the `kubernetes_namespace` from the deployer "
        "component configuration (defaults to 'zenml-deployments').",
    )

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: Optional[str]) -> Optional[str]:
        """Validate Kubernetes namespace name.

        Args:
            v: The namespace value to validate.

        Returns:
            The validated namespace value.

        Raises:
            ValueError: If the namespace is invalid.
        """
        if v is None:
            return v

        import re

        # Kubernetes namespace naming rules:
        # - Must be lowercase alphanumeric or hyphens
        # - Must start and end with alphanumeric
        # - Max 63 characters
        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError(
                f"Invalid namespace: '{v}'. Kubernetes namespaces must be lowercase "
                "alphanumeric characters or hyphens, and must start and end with "
                "an alphanumeric character."
            )
        if len(v) > 63:
            raise ValueError(
                f"Namespace too long: {len(v)} > 63 characters. "
                f"Kubernetes resource names must be at most 63 characters."
            )
        return v

    service_type: KubernetesServiceType = Field(
        default=KubernetesServiceType.LOAD_BALANCER,
        description=(
            "Type of Kubernetes Service: LoadBalancer, NodePort, or ClusterIP. "
            "LoadBalancer is recommended for production (requires cloud provider support). "
            "For production with custom domains and TLS, consider using ClusterIP with an Ingress."
        ),
    )

    service_port: PositiveInt = Field(
        default=8000,
        description="Port to expose on the service.",
    )

    image_pull_policy: str = Field(
        default="IfNotPresent",
        description="Kubernetes image pull policy: Always, IfNotPresent, or Never.",
    )

    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional labels to apply to all Kubernetes resources.",
    )

    annotations: Dict[str, str] = Field(
        default_factory=dict,
        description="Annotations to add to Pod resources. "
        "Example: {'prometheus.io/scrape': 'true', 'prometheus.io/port': '8000'}",
    )

    # Container configuration
    command: Optional[List[str]] = Field(
        default=None,
        description="Override container command (entrypoint). "
        "If not set, uses the image's default or ZenML's deployment server.",
    )

    args: Optional[List[str]] = Field(
        default=None,
        description="Override container args. "
        "If not set, uses defaults appropriate for the deployment.",
    )

    service_account_name: Optional[str] = Field(
        default=None,
        description="Kubernetes service account for the deployment pods. "
        "If not set, uses the default service account in the namespace.",
    )

    image_pull_secrets: List[str] = Field(
        default_factory=list,
        description="Names of Kubernetes secrets for pulling private images. "
        "Example: ['my-registry-secret', 'dockerhub-secret']",
    )

    # ========================================================================
    # Health Probes (necessary for production robustness)
    # ========================================================================

    readiness_probe_path: str = Field(
        default="/api/health",
        description="HTTP path for readiness probe.",
    )

    @field_validator("readiness_probe_path", "liveness_probe_path")
    @classmethod
    def validate_probe_path(cls, v: str) -> str:
        """Validate that probe paths start with /.

        Args:
            v: The probe path value.

        Returns:
            The validated probe path.

        Raises:
            ValueError: If the path doesn't start with /.
        """
        if not v.startswith("/"):
            raise ValueError(f"Probe path must start with '/': {v}")
        return v

    readiness_probe_initial_delay: PositiveInt = Field(
        default=10,
        description="Initial delay in seconds before starting readiness probe.",
    )

    readiness_probe_period: PositiveInt = Field(
        default=10,
        description="How often (in seconds) to perform readiness probe.",
    )

    readiness_probe_timeout: PositiveInt = Field(
        default=5,
        description="Timeout in seconds for readiness probe.",
    )

    readiness_probe_failure_threshold: PositiveInt = Field(
        default=3,
        description="Number of failures before marking pod as not ready.",
    )

    liveness_probe_path: str = Field(
        default="/api/health",
        description="HTTP path for liveness probe.",
    )

    liveness_probe_initial_delay: PositiveInt = Field(
        default=30,
        description="Initial delay in seconds before starting liveness probe.",
    )

    liveness_probe_period: PositiveInt = Field(
        default=10,
        description="How often (in seconds) to perform liveness probe.",
    )

    liveness_probe_timeout: PositiveInt = Field(
        default=5,
        description="Timeout in seconds for liveness probe.",
    )

    liveness_probe_failure_threshold: PositiveInt = Field(
        default=3,
        description="Number of failures before restarting pod.",
    )

    # ========================================================================
    # Advanced Pod Configuration
    # ========================================================================

    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Advanced pod configuration: volumes, affinity, tolerations, node selectors, etc. "
        "Use this for advanced scheduling and resource requirements.",
    )

    additional_resources: List[Union[Dict[str, Any], str]] = Field(
        default_factory=list,
        description="Additional Kubernetes resources to deploy alongside Deployment/Service. "
        "Works for ANY resource type: Ingress, HPA, NetworkPolicy, ServiceMonitor, CRDs, etc.\n\n"
        "Supports three formats:\n"
        "1. Python dicts (inline manifests)\n"
        "2. File paths to YAML files (single or multi-document)\n"
        "3. Mix of both\n\n"
        "💡 TIP: Use dry_run=True to validate all resources via Kubernetes API "
        "before actually deploying.\n\n"
        "Example 1 - Inline dicts:\n"
        "```python\n"
        "additional_resources=[\n"
        "    {'apiVersion': 'networking.k8s.io/v1', 'kind': 'Ingress', ...},\n"
        "    {'apiVersion': 'autoscaling/v2', 'kind': 'HorizontalPodAutoscaler', ...},\n"
        "]\n"
        "```\n\n"
        "Example 2 - YAML files:\n"
        "```python\n"
        "additional_resources=[\n"
        "    'k8s/ingress.yaml',  # Single resource\n"
        "    'k8s/all-resources.yaml',  # Multiple resources (separated by ---)\n"
        "]\n"
        "```\n\n"
        "Example 3 - Mixed:\n"
        "```python\n"
        "additional_resources=[\n"
        "    'k8s/ingress.yaml',  # From file\n"
        "    {'apiVersion': 'autoscaling/v2', 'kind': 'HorizontalPodAutoscaler', ...},  # Inline\n"
        "]\n"
        "```\n\n"
        "ZenML validates and applies these for you. All resources are cleaned up on deprovision.",
    )

    @field_validator("additional_resources")
    @classmethod
    def validate_additional_resources(
        cls, v: List[Union[Dict[str, Any], str]]
    ) -> List[Union[Dict[str, Any], str]]:
        """Validate additional resources format.

        Args:
            v: List of additional resources.

        Returns:
            The validated list.

        Raises:
            ValueError: If a resource dict is missing required fields.
        """
        for resource in v:
            if isinstance(resource, dict):
                if "kind" not in resource:
                    raise ValueError(
                        f"Resource dict must have 'kind' field: {resource}"
                    )
                if "apiVersion" not in resource:
                    raise ValueError(
                        f"Resource dict must have 'apiVersion' field: {resource}"
                    )
        return v

    # ========================================================================
    # Template and Development Settings
    # ========================================================================

    custom_templates_dir: Optional[str] = Field(
        default=None,
        description="Path to directory containing custom Jinja2 templates for full control. "
        "Override built-in templates (deployment.yaml.j2, service.yaml.j2, etc.). "
        "Example: '~/.zenml/k8s-templates'",
    )

    dry_run: bool = Field(
        default=False,
        description="If True, validate manifests without creating resources. "
        "Useful for testing configurations before applying them.",
    )

    save_manifests: bool = Field(
        default=False,
        description="If True, save generated YAML manifests to disk for inspection. "
        "Always enabled when dry_run=True.",
    )

    manifest_output_dir: Optional[str] = Field(
        default=None,
        description="Custom directory for saving manifests. "
        "If not provided, uses ZenML config directory. "
        "Supports path expansion: '~/my-manifests'",
    )

    # ========================================================================
    # Internal/Backward Compatibility Properties
    # ========================================================================

    wait_for_load_balancer_timeout: PositiveInt = Field(
        default=150,
        description="Timeout in seconds for LoadBalancer IP assignment. "
        "Set to 0 to skip waiting. Only applies to LoadBalancer service type.",
    )

    deployment_ready_check_interval: PositiveInt = Field(
        default=2,
        description="Interval in seconds between deployment readiness checks.",
    )


class KubernetesDeployerConfig(BaseDeployerConfig, KubernetesDeployerSettings):
    """Configuration for the Kubernetes deployer.

    This config combines deployer-specific settings with Kubernetes
    component configuration (context, namespace, in-cluster mode).

    Attributes:
        incluster: If `True`, the deployer will run inside the same cluster in which it itself is running. This requires the client to run in a Kubernetes pod itself. If set, the `kubernetes_context` config option is ignored. If the stack component is linked to a Kubernetes service connector, this field is ignored.
        kubernetes_context: Name of a Kubernetes context to run deployments in. If the stack component is linked to a Kubernetes service connector, this field is ignored. Otherwise, it is mandatory.
        kubernetes_namespace: Default Kubernetes namespace for deployments. Can be overridden per-deployment using the `namespace` setting. Defaults to 'zenml-deployments'.
        local: If `True`, the deployer will assume it is connected to a local kubernetes cluster and will perform additional validations.
    """

    incluster: bool = Field(
        False,
        description="If `True`, the deployer will run inside the "
        "same cluster in which it itself is running. This requires the client "
        "to run in a Kubernetes pod itself. If set, the `kubernetes_context` "
        "config option is ignored. If the stack component is linked to a "
        "Kubernetes service connector, this field is ignored.",
    )

    kubernetes_context: Optional[str] = Field(
        None,
        description="Name of a Kubernetes context to run deployments in. "
        "If the stack component is linked to a Kubernetes service connector, "
        "this field is ignored. Otherwise, it is mandatory.",
    )

    kubernetes_namespace: str = Field(
        "zenml-deployments",
        description="Default Kubernetes namespace for deployments. "
        "Can be overridden per-deployment using the `namespace` setting. "
        "Defaults to 'zenml-deployments'.",
    )

    local: bool = Field(
        False,
        description="If `True`, the deployer will assume it is connected to a "
        "local kubernetes cluster and will perform additional validations.",
    )

    @property
    def is_local(self) -> bool:
        """Checks if this is a local Kubernetes cluster.

        Returns:
            True if using a local Kubernetes cluster, False otherwise.
        """
        if self.kubernetes_context:
            local_context_indicators = [
                "k3d-",
                "kind-",
                "minikube",
                "docker-desktop",
                "colima",
                "rancher-desktop",
            ]
            context_lower = self.kubernetes_context.lower()
            return any(
                indicator in context_lower
                for indicator in local_context_indicators
            )
        return False

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return not self.is_local


class KubernetesDeployerFlavor(BaseDeployerFlavor):
    """Flavor for the Kubernetes deployer."""

    @property
    def name(self) -> str:
        """The name of the flavor.

        Returns:
            The flavor name.
        """
        return KUBERNETES_DEPLOYER_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector requirements for the Kubernetes deployer.

        Returns:
            Service connector requirements.
        """
        return ServiceConnectorRequirements(
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to docs about this flavor.

        Returns:
            The documentation URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to SDK docs about this flavor.

        Returns:
            The SDK documentation URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """The logo URL for the flavor.

        Returns:
            The logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png"

    @property
    def config_class(self) -> Type[KubernetesDeployerConfig]:
        """Returns `KubernetesDeployerConfig` config class.

        Returns:
            The config class.
        """
        return KubernetesDeployerConfig

    @property
    def implementation_class(self) -> Type["KubernetesDeployer"]:
        """Returns the implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubernetes.deployers import (
            KubernetesDeployer,
        )

        return KubernetesDeployer
