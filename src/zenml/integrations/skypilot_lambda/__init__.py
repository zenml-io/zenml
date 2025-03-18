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
"""Initialization of the Skypilot Lambda integration for ZenML.

The Skypilot integration sub-module powers an alternative to the local
orchestrator for a remote orchestration of ZenML pipelines on VMs.
"""
from typing import List, Type

from zenml.integrations.constants import (
    SKYPILOT_LAMBDA,
)
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

SKYPILOT_LAMBDA_ORCHESTRATOR_FLAVOR = "vm_lambda"


class SkypilotLambdaIntegration(Integration):
    """Definition of Skypilot Lambda Integration for ZenML."""

    NAME = SKYPILOT_LAMBDA
    REQUIREMENTS = ["skypilot[lambda]~=0.6.0"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Skypilot Lambda integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.skypilot_lambda.flavors import (
            SkypilotLambdaOrchestratorFlavor,
        )

        return [SkypilotLambdaOrchestratorFlavor]

