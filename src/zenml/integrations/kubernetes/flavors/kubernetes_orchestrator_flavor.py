#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Kubernetes orchestrator flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic import root_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes import KUBERNETES_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.orchestrators import (
        KubernetesOrchestrator,
    )


class KubernetesOrchestratorSettings(BaseSettings):
    """Settings for the Kubernetes orchestrator.

    Attributes:
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Kubernetes.
        timeout: How many seconds to wait for synchronous runs. `0` means
            to wait for an unlimited duration.
        pod_settings: Pod settings to apply.
    """

    synchronous: bool = False
    timeout: int = 0

    pod_settings: Optional[KubernetesPodSettings] = None


class KubernetesOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, KubernetesOrchestratorSettings
):
    """Configuration for the Kubernetes orchestrator.

    Attributes:
        kubernetes_context: Name of a Kubernetes context to run pipelines in.
        kubernetes_namespace: Name of the Kubernetes namespace to be used.
            If not provided, `zenml` namespace will be used.
        local: If `True`, the orchestrator will assume it is connected to a
            local kubernetes cluster and will perform additional validations and
            operations to allow using the orchestrator in combination with other
            local stack components that store data in the local filesystem
            (i.e. it will mount the local stores directory into the pipeline
            containers).
        skip_local_validations: If `True`, the local validations will be
            skipped.
    """

    kubernetes_context: str  # TODO: Potential setting
    kubernetes_namespace: str = "zenml"
    local: bool = False
    skip_local_validations: bool = False

    @root_validator(pre=True)
    def _validate_deprecated_attrs(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pydantic root_validator for deprecated attributes.

        This root validator is used for backwards compatibility purposes. E.g.
        it handles attributes that are no longer available or that have become
        mandatory in the meantime.

        Args:
            values: Values passed to the object constructor

        Returns:
            Values passed to the object constructor

        Raises:
            ValueError: If the attributes or their values are not valid.
        """
        if not values.get("kubernetes_context"):
            raise ValueError(
                "An empty value is no longer allowed for the "
                "`kubernetes_context` attribute of the Kubernetes "
                "orchestrator, to avoid unpredictable behavior. Please set "
                "the `kubernetes_context` attribute to the name of the "
                "Kubernetes config context pointing to the cluster where "
                "you would like to run pipelines."
            )

        return values

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return not self.local

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return self.local


class KubernetesOrchestratorFlavor(BaseOrchestratorFlavor):
    """Kubernetes orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return KUBERNETES_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png"

    @property
    def config_class(self) -> Type[KubernetesOrchestratorConfig]:
        """Returns `KubernetesOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return KubernetesOrchestratorConfig

    @property
    def implementation_class(self) -> Type["KubernetesOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubernetes.orchestrators import (
            KubernetesOrchestrator,
        )

        return KubernetesOrchestrator
