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

from typing import List, Type

from zenml.integrations.constants import (
    DATABRICKS,
)
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

DATABRICKS_ORCHESTRATOR_FLAVOR = "databricks"

class DatabricksIntegration(Integration):
    """Definition of Databricks Integration for ZenML."""

    NAME = DATABRICKS
    REQUIREMENTS = ["databricks-sdk"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Databricks integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.databricks.flavors import (
            DatabricksOrchestratorFlavor,
        )

        return [DatabricksOrchestratorFlavor]

DatabricksIntegration.check_installation()


from databricks.sdk import WorkspaceClient
w = WorkspaceClient(, account_id="fbe81b69-874c-4447-a150-c45e7674519c", token='dose8d22a0ab5dfd8b617b0e398b0bc35a49')

from databricks.sdk import WorkspaceClient