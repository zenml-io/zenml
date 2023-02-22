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
"""Airflow integration for ZenML.

The Airflow integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Airflow orchestrator with
the CLI tool, then bootstrap using the ``zenml orchestrator up`` command.
"""
from typing import List, Optional, Type

from zenml.integrations.constants import AIRFLOW
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

AIRFLOW_ORCHESTRATOR_FLAVOR = "airflow"


class AirflowIntegration(Integration):
    """Definition of Airflow Integration for ZenML."""

    NAME = AIRFLOW

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Airflow integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.airflow.flavors import (
            AirflowOrchestratorFlavor,
        )

        return [AirflowOrchestratorFlavor]

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Defines platform specific requirements for the integration.

        Args:
            target_os: The target operating system.

        Returns:
            A list of requirements.
        """
        return ["apache-airflow~=2.4.0"]


AirflowIntegration.check_installation()
