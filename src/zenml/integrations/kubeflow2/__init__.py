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
"""Initialization of the Kubeflow 2 integration for ZenML.

The Kubeflow 2 integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Kubeflow orchestrator with
the CLI tool.
"""
from typing import List, Type

from zenml.integrations.constants import KUBEFLOW2
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

KUBEFLOW2_ORCHESTRATOR_FLAVOR = "kubeflow2"


class Kubeflow2Integration(Integration):
    """Definition of Kubeflow 2 Integration for ZenML."""

    NAME = KUBEFLOW2
    REQUIREMENTS = ["kfp>=2.0.0"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Kubeflow 2 integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.kubeflow2.flavors import (
            Kubeflow2OrchestratorFlavor,
        )

        return [Kubeflow2OrchestratorFlavor]


Kubeflow2Integration.check_installation()
