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
"""Initialization of the Argo integration for ZenML.

The Argo integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Argo orchestrator with
the CLI tool.
"""
from typing import List, Type

from zenml.integrations.constants import ARGO
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

ARGO_ORCHESTRATOR_FLAVOR = "argo"


class ArgoIntegration(Integration):
    """Definition of Argo Integration for ZenML."""

    NAME = ARGO
    REQUIREMENTS = ["hera-workflows", "kubernetes"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Argo integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.argo.flavors import ArgoOrchestratorFlavor

        return [ArgoOrchestratorFlavor]


ArgoIntegration.check_installation()
