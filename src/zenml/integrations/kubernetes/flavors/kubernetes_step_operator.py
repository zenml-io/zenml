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
"""Kubernetes step_operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubernetes import KUBERNETES_STEP_OPERATOR_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators.base_step_operator import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.orchestrators import (
        KubernetesOrchestrator,
    )


class KubernetesStepOperatorSettings(BaseSettings):
    """Settings for the Kubernetes orchestrator.

    Attributes:
        synchronous: If `True`, the client running a pipeline using this
            step_operator waits until all steps finish running. If `False`,
            the client returns immediately and the pipeline is executed
            asynchronously. Defaults to `True`.
        timeout: How many seconds to wait for synchronous runs. `0` means
            to wait for an unlimited duration.
        service_account_name: Name of the service account to use for the
            step_operator pod. If not provided, a new service account with "edit"
            permissions will be created.
        step_pod_service_account_name: Name of the service account to use for the
            step pods. If not provided, the default service account will be used.
        privileged: If the container should be run in privileged mode.
        pod_settings: Pod settings to apply to pods executing the steps.
        step_operator_pod_settings: Pod settings to apply to the pod which is
            launching the actual steps.
    """

    synchronous: bool = True
    timeout: int = 0
    service_account_name: Optional[str] = None
    step_pod_service_account_name: Optional[str] = None
    privileged: bool = False
    pod_settings: Optional[KubernetesPodSettings] = None
    step_operator_pod_settings: Optional[KubernetesPodSettings] = None


class KubernetesStepOperatorConfig(
    BaseStepOperatorConfig, KubernetesStepOperatorSettings
):
    """Configuration for the Kubernetes step_operator.

    Attributes:
        incluster: If `True`, the step_operator will run the step inside the
            same cluster in which the pipeline itself is running. This requires the client
            to run in a Kubernetes pod itself. If set, the `kubernetes_context`
            config option is ignored. If the stack component is linked to a
            Kubernetes service connector, this field is ignored.
        kubernetes_context: Name of a Kubernetes context to run steps in.
            If the stack component is linked to a Kubernetes service connector,
            this field is ignored. Otherwise, it is mandatory.
        kubernetes_namespace: Name of the Kubernetes namespace to be used.
            If not provided, `zenml` namespace will be used.
        local: If `True`, the step_operator will assume it is connected to a
            local kubernetes cluster and will perform additional validations and
            operations to allow using the step_operator in combination with other
            local stack components that store data in the local filesystem
            (i.e. it will mount the local stores directory into the pipeline
            containers).
        skip_local_validations: If `True`, the local validations will be
            skipped.
        parallel_step_startup_waiting_period: How long to wait in between
            starting parallel steps. This can be used to distribute server
            load when running pipelines with a huge amount of parallel steps.
    """

    incluster: bool = False
    kubernetes_context: Optional[str] = None
    kubernetes_namespace: str = "zenml"
    local: bool = False
    skip_local_validations: bool = False
    parallel_step_startup_waiting_period: Optional[float] = None

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

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return self.local

    @property
    def is_synchronous(self) -> bool:
        """Whether the step_operator runs synchronous or not.

        Returns:
            Whether the step_operator runs synchronous or not.
        """
        return self.synchronous


class KubernetesStepOperatorFlavor(BaseStepOperatorFlavor):
    """Kubernetes step_operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return KUBERNETES_STEP_OPERATOR_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
        )

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/kubernetes.png"

    @property
    def config_class(self) -> Type[KubernetesStepOperatorConfig]:
        """Returns `KubernetesOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return KubernetesStepOperatorConfig

    @property
    def implementation_class(self) -> Type["KubernetesOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubernetes.step_operators import (
            KubernetesStepOperator,
        )

        return KubernetesOrchestrator
