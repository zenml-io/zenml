#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Initialization for the ZenML MLflow integration.

The MLflow integrations currently enables you to use MLflow tracking as a
convenient way to visualize your experiment runs within the MLflow UI.
"""
from typing import List, Type

from zenml.integrations.constants import MLFLOW
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

MLFLOW_MODEL_DEPLOYER_FLAVOR = "mlflow"
MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR = "mlflow"
MLFLOW_MODEL_REGISTRY_FLAVOR = "mlflow"


class MlflowIntegration(Integration):
    """Definition of MLflow integration for ZenML."""

    NAME = MLFLOW
    # We need to pin protobuf to a version <=4 here, as this mlflow release
    # does not pin it. They fixed this in a later version, so we can probably
    # remove this once we update the mlflow version.
    REQUIREMENTS = [
        "mlflow>=2.1.1,<=2.12.2",
        "mlserver>=1.3.3",
        "mlserver-mlflow>=1.3.3",
        # TODO: remove this requirement once rapidjson is fixed
        "python-rapidjson<1.15",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activate the MLflow integration."""
        from zenml.integrations.mlflow import services  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the MLflow integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.mlflow.flavors import (
            MLFlowExperimentTrackerFlavor,
            MLFlowModelDeployerFlavor,
            MLFlowModelRegistryFlavor,
        )

        return [
            MLFlowModelDeployerFlavor,
            MLFlowExperimentTrackerFlavor,
            MLFlowModelRegistryFlavor,
        ]


MlflowIntegration.check_installation()
