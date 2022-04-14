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
The Vertex integration submodule provides a way to run ZenML pipelines in a 
Vertex AI environment.
"""

from zenml.enums import StackComponentType
from zenml.integrations.constants import VERTEX
from zenml.integrations.integration import Integration
from zenml.integrations.utils import register_flavor

VERTEX_STEP_OPERATOR_FLAVOR = "vertex"


class VertexIntegration(Integration):
    """Definition of Vertex AI integration for ZenML."""

    NAME = VERTEX
    REQUIREMENTS = ["google-cloud-aiplatform>=1.11.0"]

    @classmethod
    def declare(cls) -> None:
        """Declare the stack component flavors for the Vertex integration."""
        register_flavor(
            flavor=VERTEX_STEP_OPERATOR_FLAVOR,
            source="zenml.integrations.vertex.step_operators.VertexStepOperator",
            stack_component_type=StackComponentType.STEP_OPERATOR,
            integration=cls.NAME,
        )


VertexIntegration.check_installation()
