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
"""Initialization for the VertexAI integration.

The Vertex integration submodule provides a way to run ZenML pipelines in
Vertex AI environment.
"""

from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import VERTEX
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

VERTEX_ORCHESTRATOR_FLAVOR = "vertex"
VERTEX_STEP_OPERATOR_FLAVOR = "vertex"


class VertexIntegration(Integration):
    """Definition of Vertex AI integration for ZenML."""

    NAME = VERTEX
    REQUIREMENTS = ["google-cloud-aiplatform>=1.11.0", "kfp==1.8.9"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Vertex integration.

        Returns:
            List[FlavorWrapper]: List of stack component flavors.
        """
        return [
            FlavorWrapper(
                name=VERTEX_ORCHESTRATOR_FLAVOR,
                source="zenml.integrations.vertex.orchestrators.VertexOrchestrator",
                type=StackComponentType.ORCHESTRATOR,
                integration=cls.NAME,
            ),
            FlavorWrapper(
                name=VERTEX_STEP_OPERATOR_FLAVOR,
                source="zenml.integrations.vertex.step_operators.VertexStepOperator",
                type=StackComponentType.STEP_OPERATOR,
                integration=cls.NAME,
            ),
        ]


VertexIntegration.check_installation()
