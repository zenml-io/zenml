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
from zenml.integrations.kubeflow.step_operators.trainjob_manifest_utils import (
    NUM_PROC_PER_NODE_AUTO_VALUES,
)
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.step_operators import (
        KubeflowTrainerStepOperator,
    )


def _normalize_num_proc_per_node(
    value: Union[int, str, None],
) -> Optional[Union[int, Literal["auto", "cpu", "gpu"]]]:
    """Normalizes and validates the Trainer `numProcPerNode` value.

    Args:
        value: Input value.

    Returns:
        Normalized value.

    Raises:
        ValueError: If the value is invalid.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(
            "`num_proc_per_node` must be an integer >= 1 or one of "
            "`auto`, `cpu`, `gpu`."
        )

    if isinstance(value, int):
        if value < 1:
            raise ValueError("`num_proc_per_node` must be greater than 0.")
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in NUM_PROC_PER_NODE_AUTO_VALUES:
            return normalized

        if normalized.isdigit():
            parsed = int(normalized)
            if parsed < 1:
                raise ValueError("`num_proc_per_node` must be greater than 0.")
            return parsed

    raise ValueError(
        "`num_proc_per_node` must be an integer >= 1 or one of "
        "`auto`, `cpu`, `gpu`."
    )


class KubeflowTrainerStepOperatorSettings(BaseSettings):
    """Settings for the Kubeflow Trainer step operator."""

    runtime_ref_name: str = Field(
        ...,
        description="Name of the Trainer runtime reference.",
    )
    runtime_ref_kind: str = Field(
        default="ClusterTrainingRuntime",
        description="Runtime kind for the Trainer runtime reference. "
        "Examples: 'ClusterTrainingRuntime', 'TrainingRuntime'",
    )
    runtime_ref_api_group: str = Field(
        default="trainer.kubeflow.org",
        description="API group for the Trainer runtime reference.",
    )
    num_nodes: PositiveInt = Field(
        default=1,
        description="Number of nodes to request for distributed training.",
    )
    num_proc_per_node: Optional[
        Union[PositiveInt, Literal["auto", "cpu", "gpu"]]
    ] = Field(
        default=None,
        description="Trainer processes per node. Accepts an integer value or "
        "one of `auto`, `cpu`, `gpu`.",
    )
    trainer_overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional fields merged into `spec.trainer`.",
    )
    trainer_env: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables for trainer replicas.",
    )
    pod_template_overrides: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional `spec.podTemplateOverrides` entries.",
    )
    poll_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Polling interval in seconds while watching TrainJob status.",
    )
    timeout_seconds: Optional[PositiveInt] = Field(
        default=None,
        description="Optional timeout in seconds for TrainJob completion.",
    )
    delete_trainjob_after_completion: bool = Field(
        default=False,
        description="Whether to delete the TrainJob after it reaches terminal state.",
    )
    kubernetes_namespace: str = Field(
        default="default",
        description="Kubernetes namespace where TrainJobs are created.",
    )
    incluster: bool = Field(
        default=False,
        description="Whether to use in-cluster Kubernetes authentication.",
    )
    kubernetes_context: Optional[str] = Field(
        default=None,
        description="Kubernetes context to use when not running in-cluster.",
    )
    image: Optional[str] = Field(
        default=None,
        description="Optional image override for Trainer replicas.",
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
        return _normalize_num_proc_per_node(value)

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
