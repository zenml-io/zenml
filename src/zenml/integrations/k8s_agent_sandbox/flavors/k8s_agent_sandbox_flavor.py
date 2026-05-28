#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Agent Sandbox flavor."""

from enum import Enum
from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.k8s_agent_sandbox import K8S_AGENT_SANDBOX_FLAVOR
from zenml.models import ServiceConnectorRequirements
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.k8s_agent_sandbox.sandboxes import K8sAgentSandbox


class ConnectionMode(str, Enum):
    """How the Python client talks to the agent-sandbox API in the cluster.

    Mirrors ``k8s_agent_sandbox.models`` connection-config variants.
    ``LOCAL_TUNNEL`` (the SDK default) spawns ``kubectl port-forward``
    per session, which is convenient for local dev but doesn't compose
    well with remote orchestrators. ``GATEWAY`` is the recommended
    production mode — uses a stable Gateway IP discovered via the
    cluster's Gateway API.
    """

    LOCAL_TUNNEL = "local_tunnel"
    GATEWAY = "gateway"
    DIRECT = "direct"
    IN_CLUSTER = "in_cluster"


class K8sAgentSandboxSettings(BaseSandboxSettings):
    """Per-step settings for an Agent Sandbox component.

    Inherits ``base_image`` / ``environment`` / ``copy_local_env`` /
    ``timeout_seconds`` from ``BaseSandboxSettings``. The ``base_image``
    knob is only honored when ``template_name`` is unset (inline mode);
    in template mode the image comes from the referenced
    ``SandboxTemplate`` custom resource.
    """

    template_name: Optional[str] = Field(
        default=None,
        description="Name of a pre-created SandboxTemplate custom "
        "resource in the cluster. When set the flavor uses template "
        "mode: ``client.create_sandbox(template=template_name, "
        "namespace=namespace)``. When ``None`` the flavor creates an "
        "inline SandboxTemplate per session from ``base_image`` and "
        "the active step's ``ResourceSettings``. Examples: "
        "``python-sandbox``, ``ml-workload-template``. Template mode "
        "is recommended for production; inline mode is convenient "
        "for prototyping.",
    )
    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace where the Sandbox claim is "
        "created. When ``None`` falls back to the component-level "
        "``default_namespace``. Examples: ``default``, "
        "``agent-workloads``. Must exist in the cluster and be "
        "writable by the service connector's identity.",
    )
    sandbox_ready_timeout: int = Field(
        default=180,
        description="Seconds to wait for the SandboxClaim's underlying "
        "pod to become Ready before ``create_session`` raises. "
        "Defaults to 180s. Set higher when the pod image is large or "
        "the cluster auto-scales from zero.",
        ge=1,
    )


class K8sAgentSandboxConfig(BaseSandboxConfig, K8sAgentSandboxSettings):
    """Configuration for the Agent Sandbox component.

    Inherits per-step settings so they act as component-level defaults;
    ``K8sAgentSandboxSettings`` overrides them per step.

    Authentication is handled via a linked ZenML service connector
    (``gcp`` for GKE or ``kubernetes`` for any cluster) that exposes
    a ``kubernetes-cluster`` resource. The connector mints a fresh
    kubeconfig at session-creation time, so no ``~/.kube/config``
    plumbing is required.
    """

    connection_mode: ConnectionMode = Field(
        default=ConnectionMode.GATEWAY,
        description="How the Python client reaches the agent-sandbox "
        "API in the cluster. ``gateway`` (recommended for production) "
        "uses the cluster's Gateway IP; ``local_tunnel`` spawns "
        "``kubectl port-forward`` per session; ``direct`` requires an "
        "externally reachable ``api_url``; ``in_cluster`` is for "
        "callers already running inside the cluster.",
    )
    gateway_name: str = Field(
        default="sandbox-router",
        description="Name of the Gateway resource fronting the "
        "sandbox-router service. Only consulted when "
        "``connection_mode=gateway``. Defaults match the operator's "
        "sample manifests.",
    )
    gateway_namespace: str = Field(
        default="agent-sandbox-system",
        description="Namespace where the Gateway resource lives. Only "
        "consulted when ``connection_mode=gateway``.",
    )
    api_url: Optional[str] = Field(
        default=None,
        description="Direct HTTP base URL of the sandbox-router service. "
        "Required when ``connection_mode=direct``; ignored otherwise. "
        "Example: ``http://sandbox-router.example.com``.",
    )
    default_namespace: str = Field(
        default="default",
        description="Fallback Kubernetes namespace when per-step "
        "``K8sAgentSandboxSettings.namespace`` is unset.",
    )
    default_image: str = Field(
        default="python:3.11-slim",
        description="Container image used when synthesising an inline "
        "SandboxTemplate (i.e. when no per-step ``template_name`` is "
        "set and ``base_image`` is also ``None``). Ignored in template "
        "mode.",
    )

    @property
    def is_remote(self) -> bool:
        """Agent Sandbox runs the workload on a remote Kubernetes cluster.

        Returns:
            ``True`` — the ZenML server is not the host.
        """
        return True


class K8sAgentSandboxFlavor(BaseSandboxFlavor):
    """Agent Sandbox flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            ``"k8s_agent_sandbox"``.
        """
        return K8S_AGENT_SANDBOX_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector requirements.

        Accepts any connector that exposes a ``kubernetes-cluster``
        resource — covers both the ``gcp`` connector (for GKE) and
        the raw ``kubernetes`` connector (for any cluster).

        Returns:
            ``ServiceConnectorRequirements`` declaring the
            ``kubernetes-cluster`` resource type.
        """
        return ServiceConnectorRequirements(
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """URL to user-facing docs for this flavor.

        Returns:
            The flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """URL to SDK docs for this flavor.

        Returns:
            The flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """Dashboard logo URL.

        Returns:
            The flavor logo URL.
        """
        return (
            "https://public-flavor-logos.s3.eu-central-1.amazonaws.com"
            "/orchestrator/kubernetes.png"
        )

    @property
    def config_class(self) -> Type[K8sAgentSandboxConfig]:
        """Config class.

        Returns:
            ``K8sAgentSandboxConfig``.
        """
        return K8sAgentSandboxConfig

    @property
    def implementation_class(self) -> Type["K8sAgentSandbox"]:
        """Implementation class.

        Returns:
            ``K8sAgentSandbox``.
        """
        from zenml.integrations.k8s_agent_sandbox.sandboxes import (
            K8sAgentSandbox,
        )

        return K8sAgentSandbox
