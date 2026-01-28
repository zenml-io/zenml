#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Run:AI integration for ZenML."""

from typing import List, Type

from zenml.integrations.constants import RUNAI
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

RUNAI_STEP_OPERATOR_FLAVOR = "runai"


class RunAIIntegration(Integration):
    """Definition of Run:AI integration for ZenML."""

    NAME = RUNAI
    REQUIREMENTS = [
        "runapy>=0.1.0",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Run:AI integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.runai.flavors import (
            RunAIStepOperatorFlavor,
        )

        return [RunAIStepOperatorFlavor]


RunAIIntegration.check_installation()
