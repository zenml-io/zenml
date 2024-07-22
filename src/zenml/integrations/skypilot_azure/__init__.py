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
"""Initialization of the Skypilot Azure integration for ZenML.

The Skypilot integration sub-module powers an alternative to the local
orchestrator for a remote orchestration of ZenML pipelines on VMs.
"""
from typing import List, Type

from zenml.integrations.constants import (
    SKYPILOT_AZURE,
)
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

SKYPILOT_AZURE_ORCHESTRATOR_FLAVOR = "vm_azure"


class SkypilotAzureIntegration(Integration):
    """Definition of Skypilot (Azure) Integration for ZenML."""

    NAME = SKYPILOT_AZURE
    REQUIREMENTS = ["skypilot-nightly[azure]==1.0.0.dev20240716"]
    APT_PACKAGES = ["openssh-client", "rsync"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Skypilot Azure integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.skypilot_azure.flavors import (
            SkypilotAzureOrchestratorFlavor,
        )

        return [SkypilotAzureOrchestratorFlavor]

SkypilotAzureIntegration.check_installation()
