#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
The AzureML integration submodule provides a way to run ZenML steps in AzureML.
"""

from zenml.enums import StackComponentType
from zenml.integrations.constants import AZUREML
from zenml.integrations.integration import Integration
from zenml.integrations.utils import register_flavor

AZUREML_STEP_OPERATOR_FLAVOR = "azureml"


class AzureMLIntegration(Integration):
    """Definition of AzureML integration for ZenML."""

    NAME = AZUREML
    REQUIREMENTS = ["azureml-core==1.39.0.post1"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        register_flavor(
            flavor=AZUREML_STEP_OPERATOR_FLAVOR,
            source="zenml.integrations.azureml.step_operators.AzureMLStepOperator",
            stack_component_type=StackComponentType.STEP_OPERATOR,
            integration=cls.NAME,
        )


AzureMLIntegration.check_installation()
