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
    KUBERNETES_POD = "kubernetes_pod"
    GKE_START_POD = "gke_start_pod"

    @property
    def source(self) -> str:
        """Operator source.

        Returns:
            The operator source.
        """
        return {
            OperatorType.DOCKER: "airflow.providers.docker.operators.docker.DockerOperator",
            OperatorType.KUBERNETES_POD: "airflow.providers.cncf.kubernetes.operators.kubernetes_pod.KubernetesPodOperator",
            OperatorType.GKE_START_POD: "airflow.providers.google.cloud.operators.kubernetes_engine.GKEStartPodOperator",
        }[self]


class AirflowOrchestratorSettings(BaseSettings):
    """Settings for the Airflow orchestrator.

    Attributes:
        dag_output_dir: Output directory in which to write the Airflow DAG.
        dag_id: Optional ID of the Airflow DAG to create. This value is only
            applied if the settings are defined on a ZenML pipeline and
            ignored if defined on a step.
        dag_tags: Tags to add to the Airflow DAG. This value is only
            applied if the settings are defined on a ZenML pipeline and
            ignored if defined on a step.
        dag_args: Arguments for initializing the Airflow DAG. This
            value is only applied if the settings are defined on a ZenML
            pipeline and ignored if defined on a step.
        operator: The operator to use for one or all steps. This can either be
            a `zenml.integrations.airflow.flavors.airflow_orchestrator_flavor.OperatorType`
            or a string representing the source of the operator class to use
            (e.g. `airflow.providers.docker.operators.docker.DockerOperator`)
        operator_args: Arguments for initializing the Airflow
            operator.
        custom_dag_generator: Source string of a module to use for generating
            Airflow DAGs. This module must contain the same classes and
            constants as the
            `zenml.integrations.airflow.orchestrators.dag_generator` module.
            This value is only applied if the settings are defined on a ZenML
            pipeline and ignored if defined on a step.
    """

    dag_output_dir: Optional[str] = None

    dag_id: Optional[str] = None
    dag_tags: List[str] = []
    dag_args: Dict[str, Any] = {}

    operator: str = OperatorType.DOCKER.source
    operator_args: Dict[str, Any] = {}

    custom_dag_generator: Optional[str] = None

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
        if isinstance(value, OperatorType):
            return value.source

        try:
            return OperatorType(value).source
        except ValueError:
            return value


class AirflowOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, AirflowOrchestratorSettings
):
    """Configuration for the Airflow orchestrator.

    Attributes:
        local: If the orchestrator is local or not. If this is True, will spin
            up a local Airflow server to run pipelines.
    """

    local: bool = True


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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/airflow.png"

    @property
    def config_class(self) -> Type[AirflowOrchestratorConfig]:
        """Returns `AirflowOrchestratorConfig` config class.

        Returns:
            The config class.
        """
        return AirflowOrchestratorConfig

    @property
    def implementation_class(self) -> Type["AirflowOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.airflow.orchestrators import (
            AirflowOrchestrator,
        )

        return AirflowOrchestrator
