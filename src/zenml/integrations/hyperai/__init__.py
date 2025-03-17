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
"""Initialization of the HyperAI integration."""
from typing import List, Type

from zenml.integrations.constants import HYPERAI
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

# Service connector constants
HYPERAI_CONNECTOR_TYPE = "hyperai"
HYPERAI_RESOURCE_TYPE = "hyperai-instance"


class HyperAIIntegration(Integration):
    """Definition of HyperAI integration for ZenML."""

    NAME = HYPERAI
    REQUIREMENTS = [
        "paramiko>=3.4.0",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.hyperai import service_connectors  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the HyperAI integration.
        
        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.hyperai.flavors import (
            HyperAIOrchestratorFlavor
        )

        return [HyperAIOrchestratorFlavor]

