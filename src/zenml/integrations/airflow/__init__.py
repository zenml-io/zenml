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
The Airflow integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Airflow orchestrator with
the CLI tool, then bootstrap using the ``zenml orchestrator up`` command.
"""
from zenml.integrations.constants import AIRFLOW
from zenml.integrations.integration import Integration


class AirflowIntegration(Integration):
    """Definition of Airflow Integration for ZenML."""

    NAME = AIRFLOW
    REQUIREMENTS = ["apache-airflow==2.2.0"]

    @classmethod
    def activate(cls):
        """Activates all classes required for the airflow integration."""
        from zenml.integrations.airflow import orchestrators  # noqa


AirflowIntegration.check_installation()
