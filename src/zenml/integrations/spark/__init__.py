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

"""The Spark integration module to enable distributed processing for steps."""

from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import SPARK
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

SPARK_KUBERNETES_STEP_OPERATOR = "spark-kubernetes"


class SparkIntegration(Integration):
    """Definition of Spark integration for ZenML."""

    NAME = SPARK
    REQUIREMENTS = ["pyspark==3.2.1"]

    @classmethod
    def activate(cls) -> None:
        """Activating the corresponding Spark materializers."""
        from zenml.integrations.spark import materializers  # noqa

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Spark integration.

        Returns:
            The flavor wrapper for the step operator flavor
        """
        return [
            FlavorWrapper(
                name=SPARK_KUBERNETES_STEP_OPERATOR,
                source="zenml.integrations.spark.step_operators.KubernetesSparkStepOperator",
                type=StackComponentType.STEP_OPERATOR,
                integration=cls.NAME,
            ),
        ]


SparkIntegration.check_installation()
