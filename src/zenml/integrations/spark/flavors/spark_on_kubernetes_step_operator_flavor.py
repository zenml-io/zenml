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
"""Spark on Kubernetes step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.spark import SPARK_KUBERNETES_STEP_OPERATOR
from zenml.integrations.spark.flavors.spark_step_operator_flavor import (
    SparkStepOperatorConfig,
    SparkStepOperatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.spark.step_operators import (
        KubernetesSparkStepOperator,
    )


class KubernetesSparkStepOperatorConfig(SparkStepOperatorConfig):
    """Config for the Kubernetes Spark step operator.

    Attributes:
        namespace: the namespace under which the driver and executor pods
            will run.
        service_account: the service account that will be used by various Spark
            components (to create and watch the pods).
        docker_parent_image: (which originally comes from the
            PipelineDockerImageBuilder base class) indicates the name of a
            base image that has Spark enabled.
    """

    namespace: Optional[str] = None
    service_account: Optional[str] = None


class KubernetesSparkStepOperatorFlavor(SparkStepOperatorFlavor):
    """Flavor for the Kubernetes Spark step operator."""

    @property
    def name(self) -> str:
        return SPARK_KUBERNETES_STEP_OPERATOR

    @property
    def config_class(self) -> Type[KubernetesSparkStepOperatorConfig]:
        return KubernetesSparkStepOperatorConfig

    @property
    def implementation_class(self) -> Type["KubernetesSparkStepOperator"]:
        from zenml.integrations.spark.step_operators import (
            KubernetesSparkStepOperator,
        )

        return KubernetesSparkStepOperator
