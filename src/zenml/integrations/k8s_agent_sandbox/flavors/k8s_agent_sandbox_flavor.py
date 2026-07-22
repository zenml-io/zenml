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
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.k8s_agent_sandbox.sandboxes import K8sAgentSandbox


class ConnectionMode(str, Enum):
    """How the Python client talks to the agent-sandbox API in the cluster."""

    LOCAL_TUNNEL = "local_tunnel"
    GATEWAY = "gateway"
    DIRECT = "direct"
    IN_CLUSTER = "in_cluster"


class K8sAgentSandboxSettings(BaseSandboxSettings):
    """Per-step settings for an Agent Sandbox component."""

    image: Optional[str] = Field(
        default=None,
        description="Container image used when synthesizing an inline "
        "SandboxTemplate (i.e. when ``template_name`` is unset). Must "
        "contain the agent-sandbox runtime that exposes the sandbox "
        "HTTP API on port 8888. Pin to a digest or a stable tag — "
        "never ``:latest``. Example: "
        "``ghcr.io/agent-sandbox/python-runtime@sha256:...``. Ignored "
        "when ``template_name`` is set.",
    )
    template_name: Optional[str] = Field(
        default=None,
        description="Name of a pre-created SandboxTemplate custom "
        "resource in the cluster (template mode). When ``None`` the "
        "flavor creates an inline SandboxTemplate per session from "
        "``image``, ``sandbox_environment`` and ``pod_settings``. In "
        "template mode the referenced SandboxTemplate's spec wins and "
        "the inherited ``sandbox_environment`` setting is NOT applied — "
        "bake env into the template or pass per-exec ``env``. Example: "
        "``python-sandbox``.",
    )
    namespace: str = Field(
        default="default",
        description="Kubernetes namespace where the Sandbox claim is "
        "created. Must already exist in the cluster. Example: "
        "``agent-workloads``.",
    )
    sandbox_ready_timeout: int = Field(
        default=180,
        description="Seconds to wait for the SandboxClaim's underlying "
        "pod to become Ready before ``create_session`` raises. Set "
        "higher when the pod image is large or the cluster auto-scales "
        "from zero.",
        ge=1,
    )
    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Kubernetes pod customization (node_selectors, "
        "affinity, tolerations, volume_mounts, resources, etc). Sandbox "
        "pod resources are sized exclusively via ``resources`` here — "
        "the active step's ``ResourceSettings`` are not applied to the "
        "sandbox pod. Only applied in inline-template mode (when "
        "``template_name`` is unset).",
    )


class K8sAgentSandboxConfig(BaseSandboxConfig, K8sAgentSandboxSettings):
    """Configuration for the Agent Sandbox component."""

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
        "``connection_mode=gateway``.",
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
            "/sandbox/kubernetes-agent-sandbox.svg"
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
