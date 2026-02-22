#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Monty integration for lightweight in-process sandbox execution."""

from typing import List, Type

from zenml.integrations.constants import MONTY
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

MONTY_SANDBOX_FLAVOR = "monty"


class MontyIntegration(Integration):
    """Definition of Monty integration for ZenML."""

    NAME = MONTY
    REQUIREMENTS = ["pydantic-monty"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Monty integration.

        Returns:
            List of new stack component flavors.
        """
        from zenml.integrations.monty.flavors import MontySandboxFlavor

        return [MontySandboxFlavor]
