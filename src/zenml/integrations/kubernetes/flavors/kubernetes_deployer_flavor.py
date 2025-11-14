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

from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import Field, PositiveInt, field_validator, model_validator

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.enums import KubernetesServiceType
from zenml.integrations.kubernetes import (
    KUBERNETES_DEPLOYER_FLAVOR,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.deployers import KubernetesDeployer

logger = get_logger(__name__)


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
        additional_resources: Paths to YAML files with additional K8s resources.
        custom_templates_dir: Path to custom Jinja2 templates for Deployment/Service.
          Use this to customize health probes, service annotations, etc.
    """

    namespace: str = Field(
        "zenml-deployments",
        description="Default Kubernetes namespace for deployments. "
        "Can be overridden per-deployment using the `namespace` setting. "
        "Defaults to 'zenml-deployments'.",
    )

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

    strict_additional_resources: bool = Field(
        default=True,
        description="If True (default), fail the deployment if any additional resource fails to apply. "
        "If False, log warnings for failed resources but continue with core deployment. "
        "Recommended: True for production to ensure all critical resources (HPA, NetworkPolicy, etc.) are applied.",
    )

    additional_resources: List[str] = Field(
        default_factory=list,
        description="Paths to YAML files with additional Kubernetes resources (Ingress, HPA, etc.). "
        "Supports Jinja2 templating with deployment context variables like {{namespace}}, {{service_name}}, "
        "and {{labels}}. Use `---` to separate multiple resources in one file. "
        "See docs for available template variables and examples.",
    )

    atomic_provision: bool = Field(
        default=False,
        description="If True, attempt to rollback (delete) all provisioned resources if deployment fails. "
        "Mimics Helm's --atomic flag behavior. This is best-effort cleanup, not a true transaction. "
        "If False (default), partial resources remain on failure for inspection and manual cleanup. "
        "The resource inventory is always tracked regardless of this setting.",
    )

    # ========================================================================
    # Template and Development Settings
    # ========================================================================

    custom_deployment_template_file: Optional[str] = Field(
        default=None,
        description="Path to custom Jinja2 template file for Kubernetes Deployment. "
        "Overrides the built-in deployment.yaml.j2 template. "
        "Can be a local path or remote URL. "
        "Example: '~/.zenml/k8s-templates/my-deployment.yaml.j2'",
    )

    custom_service_template_file: Optional[str] = Field(
        default=None,
        description="Path to custom Jinja2 template file for Kubernetes Service. "
        "Overrides the built-in service.yaml.j2 template. "
        "Can be a local path or remote URL. "
        "Example: '~/.zenml/k8s-templates/my-service.yaml.j2'",
    )

    # ========================================================================
    # Internal/Backward Compatibility Properties
    # ========================================================================

    wait_for_load_balancer_timeout: int = Field(
        default=150,
        ge=0,
        description="Timeout in seconds for LoadBalancer IP assignment. "
        "Set to 0 to skip waiting. Only applies to LoadBalancer service type.",
    )

    deployment_ready_check_interval: PositiveInt = Field(
        default=2,
        description="Interval in seconds between deployment readiness checks.",
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

    @model_validator(mode="after")
    def validate_interdependent_settings(self) -> "KubernetesDeployerSettings":
        """Validate settings that depend on each other.

        Returns:
            The validated settings.
        """
        # Warn if wait_for_load_balancer_timeout is set for non-LoadBalancer services
        if (
            self.service_type != "LoadBalancer"
            and self.wait_for_load_balancer_timeout > 0
        ):
            logger.warning(
                f"wait_for_load_balancer_timeout={self.wait_for_load_balancer_timeout} "
                f"is ignored for service_type={self.service_type}. "
                f"This setting only applies to LoadBalancer service type."
            )

        return self


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

    local: bool = Field(
        False,
        description="If `True`, the deployer will assume it is connected to a "
        "local kubernetes cluster and will perform additional validations.",
    )

    skip_local_validations: bool = Field(
        False,
        description="If `True`, the local validations will be skipped.",
    )

    @property
    def is_local(self) -> bool:
        """Checks if this is a local Kubernetes cluster.

        Returns:
            True if using a local Kubernetes cluster, False otherwise.
        """
        if self.local:
            return True
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
