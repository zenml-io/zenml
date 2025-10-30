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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import Field, PositiveInt

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

    Attributes:
        namespace: Kubernetes namespace for deployments.
        service_type: Type of Kubernetes Service (LoadBalancer, NodePort, ClusterIP).
        service_port: Port to expose on the service.
        node_port: Specific NodePort (only for NodePort service type).
        image_pull_policy: Kubernetes image pull policy.
        labels: Labels to apply to all resources.
        annotations: Annotations to apply to pod resources.
        service_annotations: Annotations to apply to Service resources.
        session_affinity: Session affinity for the Service (ClientIP or None).
        load_balancer_ip: Static IP for LoadBalancer service type.
        load_balancer_source_ranges: CIDR blocks allowed to access LoadBalancer.
        command: Override container command (entrypoint).
        args: Override container args.
        readiness_probe_initial_delay: Seconds before first readiness probe after container start.
        readiness_probe_period: Seconds between readiness probe checks.
        readiness_probe_timeout: Seconds before readiness probe times out.
        readiness_probe_failure_threshold: Failed probes before marking container as not ready.
        liveness_probe_initial_delay: Seconds before first liveness probe after container start.
        liveness_probe_period: Seconds between liveness probe checks.
        liveness_probe_timeout: Seconds before liveness probe times out.
        liveness_probe_failure_threshold: Failed probes before restarting container.
        service_account_name: Kubernetes service account for the deployment pods.
        image_pull_secrets: Names of Kubernetes secrets for pulling private images.
        pod_settings: Advanced pod configuration settings.
        ingress_enabled: Enable Ingress resource creation for external access.
        ingress_class: Ingress class name to use (e.g., 'nginx', 'traefik').
        ingress_host: Hostname for the Ingress (e.g., 'my-app.example.com').
        ingress_path: Path prefix for the Ingress rule (e.g., '/', '/api').
        ingress_path_type: Path matching type: 'Prefix', 'Exact', or 'ImplementationSpecific'.
        ingress_tls_enabled: Enable TLS/HTTPS for the Ingress.
        ingress_tls_secret_name: Name of the Kubernetes Secret containing TLS certificate and key.
        ingress_annotations: Annotations for the Ingress resource.
    """

    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace for deployments. "
        "If not provided, uses the `kubernetes_namespace` from the deployer "
        "component configuration (defaults to 'zenml').",
    )
    service_type: KubernetesServiceType = Field(
        default=KubernetesServiceType.LOAD_BALANCER,
        description=(
            "Type of Kubernetes Service: LoadBalancer, NodePort, or ClusterIP. "
            "LoadBalancer is recommended for production (requires cloud provider support). "
            "NodePort has limitations: nodes may lack external IPs or be behind firewalls, "
            "making the service unreachable. For production with custom domains and TLS, "
            "consider using ClusterIP with a manually configured Ingress resource."
        ),
    )
    service_port: PositiveInt = Field(
        default=8000,
        description="Port to expose on the service.",
    )
    node_port: Optional[PositiveInt] = Field(
        default=None,
        description="Specific port on each node (NodePort type only). "
        "Must be in range 30000-32767. If not specified, Kubernetes assigns one.",
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
        description="Annotations to apply to pod resources.",
    )
    service_annotations: Dict[str, str] = Field(
        default_factory=dict,
        description="Annotations to apply to Service resources. "
        "Useful for cloud provider-specific configurations.",
    )
    session_affinity: Optional[str] = Field(
        default=None,
        description="Session affinity for the Service. Set to 'ClientIP' to enable.",
    )
    load_balancer_ip: Optional[str] = Field(
        default=None,
        description="Static IP address for LoadBalancer type Services. "
        "Cloud provider must support this feature.",
    )
    load_balancer_source_ranges: List[str] = Field(
        default_factory=list,
        description="CIDR blocks allowed to access LoadBalancer. "
        "Example: ['10.0.0.0/8', '192.168.0.0/16']",
    )

    # Container configuration
    command: Optional[List[str]] = Field(
        default=None,
        description="Override container command (entrypoint). "
        "If not set, uses the image's default CMD/ENTRYPOINT.",
    )
    args: Optional[List[str]] = Field(
        default=None,
        description="Override container args. "
        "If not set, uses the image's default CMD.",
    )

    # Probe configuration
    readiness_probe_initial_delay: PositiveInt = Field(
        default=10,
        description="Seconds before first readiness probe after container start.",
    )
    readiness_probe_period: PositiveInt = Field(
        default=10,
        description="Seconds between readiness probe checks.",
    )
    readiness_probe_timeout: PositiveInt = Field(
        default=5,
        description="Seconds before readiness probe times out.",
    )
    readiness_probe_failure_threshold: PositiveInt = Field(
        default=3,
        description="Failed probes before marking container as not ready.",
    )
    liveness_probe_initial_delay: PositiveInt = Field(
        default=30,
        description="Seconds before first liveness probe after container start.",
    )
    liveness_probe_period: PositiveInt = Field(
        default=10,
        description="Seconds between liveness probe checks.",
    )
    liveness_probe_timeout: PositiveInt = Field(
        default=5,
        description="Seconds before liveness probe times out.",
    )
    liveness_probe_failure_threshold: PositiveInt = Field(
        default=3,
        description="Failed probes before restarting container.",
    )
    liveness_probe_path: str = Field(
        default="/api/health",
        description="HTTP path for liveness probe health checks.",
    )
    readiness_probe_path: str = Field(
        default="/api/health",
        description="HTTP path for readiness probe health checks.",
    )

    # Security and access control
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

    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Advanced pod configuration: volumes, affinity, tolerations, etc.",
    )

    # Ingress configuration
    ingress_enabled: bool = Field(
        default=False,
        description="Enable Ingress resource creation for external access. "
        "When enabled, an Ingress will be created in addition to the Service. "
        "Requires an Ingress Controller (nginx, traefik, etc.) in the cluster.",
    )
    ingress_class: Optional[str] = Field(
        default=None,
        description="Ingress class name to use (e.g., 'nginx', 'traefik'). "
        "If not specified, uses the cluster's default Ingress class. "
        "The Ingress Controller for this class must be installed in the cluster.",
    )
    ingress_host: Optional[str] = Field(
        default=None,
        description="Hostname for the Ingress (e.g., 'my-app.example.com'). "
        "If not specified, the Ingress will match all hosts. "
        "Required for TLS configuration.",
    )
    ingress_path: str = Field(
        default="/",
        description="Path prefix for the Ingress rule (e.g., '/', '/api'). "
        "Defaults to '/' (match all paths).",
    )
    ingress_path_type: str = Field(
        default="Prefix",
        description="Path matching type: 'Prefix', 'Exact', or 'ImplementationSpecific'. "
        "Defaults to 'Prefix' (matches the path and all sub-paths).",
    )
    ingress_tls_enabled: bool = Field(
        default=False,
        description="Enable TLS/HTTPS for the Ingress. "
        "Requires 'ingress_tls_secret_name' to be set.",
    )
    ingress_tls_secret_name: Optional[str] = Field(
        default=None,
        description="Name of the Kubernetes Secret containing TLS certificate and key. "
        "Required when 'ingress_tls_enabled' is True. "
        "The secret must exist in the same namespace and contain 'tls.crt' and 'tls.key'.",
    )
    ingress_annotations: Dict[str, str] = Field(
        default_factory=dict,
        description="Annotations for the Ingress resource. "
        "Use controller-specific annotations for advanced configuration. "
        "Examples:\n"
        "  nginx: {'nginx.ingress.kubernetes.io/rewrite-target': '/'}\n"
        "  traefik: {'traefik.ingress.kubernetes.io/router.entrypoints': 'web'}\n"
        "  AWS ALB: {'alb.ingress.kubernetes.io/scheme': 'internet-facing'}",
    )

    # Autoscaling configuration
    hpa_manifest: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional HorizontalPodAutoscaler (HPA) manifest for autoscaling. "
        "If provided, ZenML will create/update this HPA alongside the Deployment. "
        "The HPA must target the deployment created by this deployer. "
        "Use the autoscaling/v2 API. "
        "Example:\n"
        "  {\n"
        '    "apiVersion": "autoscaling/v2",\n'
        '    "kind": "HorizontalPodAutoscaler",\n'
        '    "metadata": {"name": "my-hpa"},\n'
        '    "spec": {\n'
        '      "scaleTargetRef": {\n'
        '        "apiVersion": "apps/v1",\n'
        '        "kind": "Deployment",\n'
        '        "name": "<deployment-name>"\n'
        "      },\n"
        '      "minReplicas": 2,\n'
        '      "maxReplicas": 10,\n'
        '      "metrics": [\n'
        '        {"type": "Resource", "resource": {"name": "cpu", '
        '"target": {"type": "Utilization", "averageUtilization": 75}}}\n'
        "      ]\n"
        "    }\n"
        "  }\n"
        "See: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/",
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
        # Check if context indicates a local cluster
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
        return self.local

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
