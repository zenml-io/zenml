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
"""Kubeflow Trainer step operator flavor."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
)

from pydantic import Field, PositiveInt, field_validator

from zenml.config.base_settings import BaseSettings
from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubeflow import KUBEFLOW_TRAINER_STEP_OPERATOR_FLAVOR
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.step_operators import (
        KubeflowTrainerStepOperator,
    )


class KubeflowTrainerStepOperatorSettings(BaseSettings):
    """Settings for the Kubeflow Trainer step operator."""

    runtime_ref_name: str = Field(
        ...,
        description="Specifies the Kubeflow Trainer runtime reference name "
        "that defines the training framework. "
        "Examples: 'torch-distributed', 'mpi-v2'",
    )
    runtime_ref_kind: str = Field(
        default="ClusterTrainingRuntime",
        description="Determines the kind of Trainer runtime reference. "
        "Examples: 'ClusterTrainingRuntime' (cluster-scoped), "
        "'TrainingRuntime' (namespace-scoped)",
    )
    runtime_ref_api_group: str = Field(
        default="trainer.kubeflow.org",
        description="Specifies the API group for the Trainer runtime "
        "reference. Defaults to 'trainer.kubeflow.org'",
    )
    num_nodes: PositiveInt = Field(
        default=1,
        description="Controls the number of worker nodes for distributed "
        "training. Example: 4 for a 4-node distributed job",
    )
    num_proc_per_node: Optional[
        Union[PositiveInt, Literal["auto", "cpu", "gpu"]]
    ] = Field(
        default=None,
        description="Configures the number of processes per node. Accepts a "
        "positive integer or one of 'auto', 'cpu', 'gpu'. "
        "Example: 2 for two processes per node",
    )
    trainer_overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specifies additional fields deep-merged into the "
        "TrainJob `spec.trainer` section. "
        "Example: {'numProcPerNode': 'gpu'}",
    )
    trainer_env: Dict[str, str] = Field(
        default_factory=dict,
        description="Configures additional environment variables injected "
        "into trainer replica pods. "
        "Example: {'NCCL_DEBUG': 'INFO', 'OMP_NUM_THREADS': '1'}",
    )
    pod_template_overrides: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Specifies optional TrainJob "
        "`spec.podTemplateOverrides` entries for customizing pod "
        "specs per replica type",
    )
    poll_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Controls how frequently the operator polls for "
        "TrainJob status updates, in seconds. Example: 10.0",
    )
    timeout_seconds: Optional[PositiveInt] = Field(
        default=None,
        description="Configures an optional timeout in seconds for "
        "TrainJob completion. If exceeded, the step fails. "
        "Example: 3600 for a one-hour timeout",
    )
    delete_trainjob_after_completion: bool = Field(
        default=False,
        description="Controls whether the TrainJob resource is deleted "
        "after reaching a terminal state. Set to False to keep "
        "the resource for debugging",
    )
    kubernetes_namespace: str = Field(
        default="default",
        description="Specifies the Kubernetes namespace where TrainJobs "
        "are created and managed. Example: 'training'",
    )
    incluster: bool = Field(
        default=False,
        description="Controls whether to use in-cluster Kubernetes "
        "authentication. Set to True when the step operator "
        "runs inside a Kubernetes pod",
    )
    kubernetes_context: Optional[str] = Field(
        default=None,
        description="Specifies the kubeconfig context to use when not "
        "running in-cluster. Example: 'my-cluster-context'",
    )
    image: Optional[str] = Field(
        default=None,
        description="Configures an optional Docker image override for "
        "Trainer replicas. Example: "
        "'my-registry.io/training:v1.2'",
    )

    @field_validator("num_proc_per_node", mode="before")
    @classmethod
    def _validate_num_proc_per_node(
        cls, value: Union[int, str, None]
    ) -> Optional[Union[int, Literal["auto", "cpu", "gpu"]]]:
        """Validates and normalizes `num_proc_per_node`.

        Args:
            value: Raw input value.

        Returns:
            Normalized value.
        """
        from zenml.integrations.kubeflow.step_operators.trainjob_manifest_utils import (
            normalize_num_proc_per_node,
        )

        return normalize_num_proc_per_node(value)

    @field_validator("pod_template_overrides", mode="before")
    @classmethod
    def _normalize_pod_template_overrides(
        cls, value: Union[None, Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Normalizes pod template overrides to a list.

        Args:
            value: Raw input value.

        Returns:
            List of pod template overrides.
        """
        if value is None:
            return []

        if isinstance(value, dict):
            return [value]

        return value


class KubeflowTrainerStepOperatorConfig(
    BaseStepOperatorConfig,
    KubeflowTrainerStepOperatorSettings,
):
    """Configuration for the Kubeflow Trainer step operator."""

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component runs remotely.

        Returns:
            Always `True` for this flavor.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component runs locally.

        Returns:
            Always `False` for this flavor.
        """
        return False


class KubeflowTrainerStepOperatorFlavor(BaseStepOperatorFlavor):
    """Kubeflow Trainer step operator flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            The flavor name.
        """
        return KUBEFLOW_TRAINER_STEP_OPERATOR_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector requirements for this flavor.

        Returns:
            Kubernetes cluster connector requirements.
        """
        return ServiceConnectorRequirements(
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """Documentation URL for this flavor.

        Returns:
            The generated docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """SDK docs URL for this flavor.

        Returns:
            The generated SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """Logo URL for this flavor.

        Returns:
            Kubeflow logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubeflow.png"

    @property
    def config_class(self) -> Type[KubeflowTrainerStepOperatorConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return KubeflowTrainerStepOperatorConfig

    @property
    def implementation_class(self) -> Type["KubeflowTrainerStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The step operator implementation class.
        """
        from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_operator import (  # noqa: E501
            KubeflowTrainerStepOperator,
        )

        return KubeflowTrainerStepOperator
