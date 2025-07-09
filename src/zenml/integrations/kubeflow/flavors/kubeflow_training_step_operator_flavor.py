#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Kubeflow Training step operator flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.step_operators import (
        KubeflowTrainingStepOperator,
    )

KUBEFLOW_TRAINING_STEP_OPERATOR_FLAVOR = "kubeflow_training"


class KubeflowTrainingStepOperatorSettings(BaseSettings):
    """Settings for the Kubeflow Training step operator.

    Attributes:
        training_job_type: Type of training job to create. Supports:
            "PyTorch", "TensorFlow", "JAX", "MPI". Defaults to "PyTorch".
        num_workers: Number of worker replicas for the training job.
        num_ps: Number of parameter server replicas (TFJob only).
        restart_policy: Restart policy for the training job pods.
        clean_pod_policy: When to clean up the job pods after completion.
        ttl_seconds_after_finished: TTL for the training job after completion.
        pod_template_spec: Additional pod template specification to apply
            to training job pods.
        worker_pod_settings: Pod settings to apply to worker pods.
        master_pod_settings: Pod settings to apply to master/chief pods.
        ps_pod_settings: Pod settings to apply to parameter server pods (TFJob only).
        service_account_name: Name of the service account to use for the pods.
        pod_startup_timeout: Maximum time to wait for pods to start (in seconds).
        job_completion_timeout: Maximum time to wait for job completion (in seconds).
    """

    training_job_type: str = Field(
        default="PyTorch",
        description="Type of training job to create",
    )
    num_workers: int = Field(
        default=1,
        ge=1,
        description="Number of worker replicas",
    )
    num_ps: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of parameter server replicas (TFJob only)",
    )
    restart_policy: str = Field(
        default="OnFailure",
        description="Restart policy for training job pods",
    )
    clean_pod_policy: str = Field(
        default="All",
        description="When to clean up job pods after completion",
    )
    ttl_seconds_after_finished: Optional[int] = Field(
        default=None,
        ge=0,
        description="TTL for job cleanup after completion",
    )
    pod_template_spec: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional pod template specification",
    )
    worker_pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod settings for worker pods",
    )
    master_pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod settings for master/chief pods",
    )
    ps_pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod settings for parameter server pods",
    )
    service_account_name: Optional[str] = Field(
        default=None,
        description="Service account name for the pods",
    )
    pod_startup_timeout: int = Field(
        default=600,
        ge=1,
        description="Maximum time to wait for pods to start (seconds)",
    )
    job_completion_timeout: int = Field(
        default=3600,
        ge=1,
        description="Maximum time to wait for job completion (seconds)",
    )


class KubeflowTrainingStepOperatorConfig(
    BaseStepOperatorConfig, KubeflowTrainingStepOperatorSettings
):
    """Configuration for the Kubeflow Training step operator.

    Attributes:
        kubeflow_namespace: Name of the Kubernetes namespace where Kubeflow
            Training Operator is deployed. Defaults to "kubeflow".
        incluster: If `True`, the step operator will run inside the same
            cluster. For this to work, the pod running the orchestrator needs
            permissions to create training jobs. If set, `kubernetes_context`
            is ignored. If the stack component is linked to a Kubernetes
            service connector, this field is ignored.
        kubernetes_context: Name of a Kubernetes context to use. If the stack
            component is linked to a Kubernetes service connector, this field
            is ignored. Otherwise, it is mandatory.
    """

    kubeflow_namespace: str = Field(
        default="kubeflow",
        description="Kubernetes namespace for Kubeflow Training Operator",
    )
    incluster: bool = Field(
        default=False,
        description="Whether to run inside the same cluster",
    )
    kubernetes_context: Optional[str] = Field(
        default=None,
        description="Kubernetes context to use",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False


class KubeflowTrainingStepOperatorFlavor(BaseStepOperatorFlavor):
    """Kubeflow Training step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return KUBEFLOW_TRAINING_STEP_OPERATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/kubeflow.png"

    @property
    def config_class(self) -> Type[KubeflowTrainingStepOperatorConfig]:
        """Returns `KubeflowTrainingStepOperatorConfig` config class.

        Returns:
                The config class.
        """
        return KubeflowTrainingStepOperatorConfig

    @property
    def implementation_class(self) -> Type["KubeflowTrainingStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubeflow.step_operators import (
            KubeflowTrainingStepOperator,
        )

        return KubeflowTrainingStepOperator
