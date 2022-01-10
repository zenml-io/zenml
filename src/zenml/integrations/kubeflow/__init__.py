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
The Kubeflow integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Kubeflow orchestrator with
the CLI tool.
"""
from zenml.integrations.constants import KUBEFLOW
from zenml.integrations.integration import Integration


class KubeflowIntegration(Integration):
    """Definition of Kubeflow Integration for ZenML."""

    NAME = KUBEFLOW
    REQUIREMENTS = ["kfp==1.8.9"]

    @classmethod
    def activate(cls) -> None:
        """Activates all classes required for the airflow integration."""
        from zenml.integrations.kubeflow import metadata  # noqa
        from zenml.integrations.kubeflow import orchestrators  # noqa


KubeflowIntegration.check_installation()
