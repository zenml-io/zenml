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
"""Initialization of the Lightning integration for ZenML."""

from typing import List, Type

from zenml.integrations.constants import (
    LIGHTNING,
)
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

LIGHTNING_ORCHESTRATOR_FLAVOR = "lightning"


class LightningIntegration(Integration):
    """Definition of Lightning Integration for ZenML."""

    NAME = LIGHTNING
    REQUIREMENTS = ["lightning-sdk"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Lightning integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.lightning.flavors import (
            LightningOrchestratorFlavor,
            LightningModelDeployerFlavor,
        )

        return [
            LightningOrchestratorFlavor,
            LightningModelDeployerFlavor,
        ]

LightningIntegration.check_installation()