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
from typing import List, Type

from zenml.integrations.constants import AIRFLOW
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

AIRFLOW_ORCHESTRATOR_FLAVOR = "airflow"


class AirflowIntegration(Integration):
    """Definition of Airflow Integration for ZenML."""

    NAME = AIRFLOW
    # remove pendulum version requirement once Airflow supports
    # pendulum>-3.0.0
    REQUIREMENTS = [
        "apache-airflow~=2.4.0",
        "pendulum<3.0.0",
        # We need to add this as an extra dependency to manually downgrade
        # SQLModel. Otherwise, the initial installation of ZenML installs
        # a higher version SQLModel and a version mismatch is created.
        "sqlmodel>=0.0.9,<=0.0.16",
        # Unless we don't limit this, zenml up fails due to a version mismatch.
        "starlette<=0.27.0"
    ]

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


AirflowIntegration.check_installation()
