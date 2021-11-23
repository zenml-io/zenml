#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from zenml.integrations.constants import AIRFLOW
from zenml.integrations.integration import Integration
from zenml.utils.source_utils import import_class_by_path


class AirflowIntegration(Integration):
    """Definition of Airflow Integration for ZenML."""

    NAME = AIRFLOW
    REQUIREMENTS = ["apache-airflow==2.2.0"]

    @classmethod
    def activate(cls):
        """Activates all classes required for the airflow integration."""
        import_class_by_path(
            "zenml.integrations.airflow.orchestrators.airflow_orchestrator."
            "AirflowOrchestrator"
        )


AirflowIntegration.check_installation()
