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
"""Initialization of the Databricks integration for ZenML."""

from typing import List, Type, Optional

from zenml.integrations.constants import DATABRICKS

from zenml.integrations.integration import Integration
from zenml.stack import Flavor

DATABRICKS_ORCHESTRATOR_FLAVOR = "databricks"
DATABRICKS_MODEL_DEPLOYER_FLAVOR = "databricks"
DATABRICKS_SERVICE_ARTIFACT = "databricks_deployment_service"


class DatabricksIntegration(Integration):
    """Definition of Databricks Integration for ZenML."""

    NAME = DATABRICKS
    REQUIREMENTS = ["databricks-sdk==0.28.0"]

    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["numpy", "pandas"]

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.

        Returns:
            A list of requirements.
        """
        from zenml.integrations.numpy import NumpyIntegration
        from zenml.integrations.pandas import PandasIntegration

        return cls.REQUIREMENTS + \
            NumpyIntegration.get_requirements(target_os=target_os) + \
            PandasIntegration.get_requirements(target_os=target_os)

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Databricks integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.databricks.flavors import (
            DatabricksOrchestratorFlavor,
            DatabricksModelDeployerFlavor,
        )

        return [
            DatabricksOrchestratorFlavor,
            DatabricksModelDeployerFlavor,
        ]
