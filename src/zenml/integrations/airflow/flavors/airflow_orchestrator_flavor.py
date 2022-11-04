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
"""Airflow orchestrator flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.airflow import AIRFLOW_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.airflow.orchestrators import AirflowOrchestrator

from enum import Enum


class OperatorType(Enum):
    """Airflow operator types."""

    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    GKE_START_POD = "gke_start_pod"

    @property
    def source(self) -> str:
        """Operator source.

        Returns:
            The operator source.
        """
        return {
            OperatorType.DOCKER: "airflow.providers.docker.operators.docker.DockerOperator",
            OperatorType.KUBERNETES: "airflow.providers.cncf.kubernetes.operators.kubernetes_pod.KubernetesPodOperator",
            OperatorType.GKE_START_POD: "airflow.providers.google.cloud.operators.kubernetes_engine.GKEStartPodOperator",
        }[self]


class AirflowOrchestratorSettings(BaseSettings):
    """Settings for the Airflow orchestrator.

    Attributes:
        dag_id: Optional ID of the Airflow DAG to create. This value is only
            applied if the settings are defined on a ZenML pipeline and
            ignored if defined on a step.
        dag_tags: Tags to add to the Airflow DAG. This value is only
            applied if the settings are defined on a ZenML pipeline and
            ignored if defined on a step.
        dag_kwargs: Keyword arguments for initializing the Airflow DAG. This
            value is only applied if the settings are defined on a ZenML
            pipeline and ignored if defined on a step.
        operator: The operator to use for one or all steps. This can either be
            a `zenml.integrations.airflow.flavors.airflow_orchestrator_flavor.OperatorType`
            or a string representing the source of the operator class to use
            (e.g. `airflow.providers.docker.operators.docker.DockerOperator`)
        operator_kwargs: Keyword arguments for initializing the Airflow
            operator.
    """

    dag_id: Optional[str] = None
    dag_tags: List[str] = []
    dag_kwargs: Dict[str, Any] = {}

    operator: str = OperatorType.DOCKER.source
    operator_kwargs: Dict[str, Any] = {}

    @validator("operator", always=True)
    def _convert_operator(
        cls, value: Optional[Union[str, OperatorType]]
    ) -> Optional[str]:
        """Converts operator types to source strings.

        Args:
            value: The operator type value.

        Returns:
            The operator source.
        """
        try:
            return OperatorType(value).source
        except ValueError:
            return value


class AirflowOrchestratorConfig(BaseOrchestratorConfig):
    """Configuration for the Airflow orchestrator.

    Attributes:
        local: If the orchestrator is local or not. If this is True, will spin
            up a local Airflow server to run pipelines.
        dag_output_dir: Output directory in which to write the Airflow DAGs.
    """

    local: bool = True
    dag_output_dir: Optional[str] = None


class AirflowOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Airflow orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AIRFLOW_ORCHESTRATOR_FLAVOR

    @property
    def implementation_class(self) -> Type["AirflowOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.airflow.orchestrators import AirflowOrchestrator

        return AirflowOrchestrator
