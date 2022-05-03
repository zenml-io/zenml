#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""
The mlflow integrations currently enables you to use mlflow tracking as a
convenient way to visualize your experiment runs within the mlflow ui
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import MLFLOW
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

MLFLOW_MODEL_DEPLOYER_FLAVOR = "mlflow"
MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR = "mlflow"


class MlflowIntegration(Integration):
    """Definition of MLflow integration for ZenML."""

    NAME = MLFLOW
    REQUIREMENTS = [
        "mlflow>=1.2.0",
        "mlserver>=0.5.3",
        "mlserver-mlflow>=0.5.3",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activate the MLflow integration."""
        from zenml.integrations.mlflow import services  # noqa

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the MLflow integration"""
        return [
            FlavorWrapper(
                name=MLFLOW_MODEL_DEPLOYER_FLAVOR,
                source="zenml.integrations.mlflow.model_deployers.MLFlowModelDeployer",
                type=StackComponentType.MODEL_DEPLOYER,
                integration=cls.NAME,
            ),
            FlavorWrapper(
                name=MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR,
                source="zenml.integrations.mlflow.experiment_trackers.MLFlowExperimentTracker",
                type=StackComponentType.EXPERIMENT_TRACKER,
                integration=cls.NAME,
            ),
        ]


MlflowIntegration.check_installation()
