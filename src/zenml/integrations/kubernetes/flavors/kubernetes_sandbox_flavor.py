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
"""Kubernetes sandbox flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field, PositiveInt

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubernetes import KUBERNETES_SANDBOX_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.sandboxes.base import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.sandboxes import KubernetesSandbox


class KubernetesSandboxSettings(BaseSandboxSettings):
    """Settings for the Kubernetes sandbox."""

    image: str = Field(
        default="python:3.11-slim",
        description="Container image used for sandbox session pods.",
    )
    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod configuration overrides for sandbox session pods.",
    )
    service_account_name: Optional[str] = Field(
        default=None,
        description="Service account assigned to sandbox session pods.",
    )
    automount_service_account_token: bool = Field(
        default=False,
        description="Whether to mount a Kubernetes API token into sandbox "
        "pods, which grants in-pod cluster API access.",
    )
    privileged: bool = Field(
        default=False,
        description="Whether sandbox session containers run in privileged mode.",
    )
    pod_startup_timeout: PositiveInt = Field(
        default=120,
        description="Maximum number of seconds to wait for a sandbox pod to "
        "reach the running phase.",
    )
    api_request_timeout: Optional[PositiveInt] = Field(
        default=None,
        description="Timeout for Kubernetes API requests in seconds.",
    )


class KubernetesSandboxConfig(BaseSandboxConfig, KubernetesSandboxSettings):
    """Configuration for the Kubernetes sandbox."""

    kubernetes_namespace: str = Field(
        default="zenml",
        description="Kubernetes namespace where sandbox pods are created.",
    )
    incluster: bool = Field(
        default=False,
        description="Whether to load in-cluster Kubernetes credentials.",
    )
    kubernetes_context: Optional[str] = Field(
        default=None,
        description="Kubernetes context to use when running out-of-cluster.",
    )

    @property
    def is_remote(self) -> bool:
        """Whether this stack component runs remotely.

        Returns:
            `True`, because sandbox execution happens in Kubernetes pods.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Whether this stack component runs locally.

        Returns:
            `False`.
        """
        return False


class KubernetesSandboxFlavor(BaseSandboxFlavor):
    """Kubernetes sandbox flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The flavor name.
        """
        return KUBERNETES_SANDBOX_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector requirements for this flavor.

        Returns:
            Requirements for compatible service connectors.
        """
        return ServiceConnectorRequirements(
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to docs for this flavor.

        Returns:
            Flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to SDK docs for this flavor.

        Returns:
            Flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent this flavor in the dashboard.

        Returns:
            Flavor logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/sandbox/kubernetes.png"

    @property
    def config_class(self) -> Type[KubernetesSandboxConfig]:
        """Configuration class for this flavor.

        Returns:
            `KubernetesSandboxConfig`.
        """
        return KubernetesSandboxConfig

    @property
    def implementation_class(self) -> Type["KubernetesSandbox"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubernetes.sandboxes import KubernetesSandbox

        return KubernetesSandbox
