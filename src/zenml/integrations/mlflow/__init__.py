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
from packaging import version
from typing import List, Type, Optional

from zenml.integrations.constants import MLFLOW
from zenml.integrations.integration import Integration
from zenml.stack import Flavor
import sys

from zenml.logger import get_logger

MLFLOW_MODEL_DEPLOYER_FLAVOR = "mlflow"
MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR = "mlflow"
MLFLOW_MODEL_REGISTRY_FLAVOR = "mlflow"

logger = get_logger(__name__)


class MlflowIntegration(Integration):
    """Definition of MLflow integration for ZenML."""

    NAME = MLFLOW

    REQUIREMENTS_IGNORED_ON_UNINSTALL = [
        "python-rapidjson",
        "pydantic",
        "numpy",
        "pandas",
    ]

    @classmethod
    def get_requirements(
        cls, target_os: Optional[str] = None, python_version: Optional[str] = None
    ) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.
            python_version: The Python version to use for the requirements.

        Returns:
            A list of requirements.
        """
        from zenml.integrations.numpy import NumpyIntegration
        from zenml.integrations.pandas import PandasIntegration
        
        reqs = [
            "mlflow>=2.1.1,<3",
            # TODO: remove this requirement once rapidjson is fixed
            "python-rapidjson<1.15",
        ]

        reqs.extend(NumpyIntegration.get_requirements(target_os=target_os, python_version=python_version))
        reqs.extend(PandasIntegration.get_requirements(target_os=target_os, python_version=python_version))
        return reqs

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

