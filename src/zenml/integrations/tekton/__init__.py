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
"""Initialization of the Tekton integration for ZenML.

The Tekton integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Tekton orchestrator with
the CLI tool.
"""
from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import TEKTON
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

TEKTON_ORCHESTRATOR_FLAVOR = "tekton"


class TektonIntegration(Integration):
    """Definition of Tekton Integration for ZenML."""

    NAME = TEKTON
    REQUIREMENTS = ["kfp>=2.6.0", "kfp-kubernetes>=1.1.0"]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["kfp"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Tekton integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.tekton.flavors import TektonOrchestratorFlavor

        return [TektonOrchestratorFlavor]


TektonIntegration.check_installation()
