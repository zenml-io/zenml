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
"""Baseten integration for ZenML."""

from typing import List, Type
from zenml.integrations.constants import BASETEN
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

from zenml.integrations.baseten.flavors import (
    BasetenModelDeployerConfig,
    BasetenModelDeployerFlavor,
)
from zenml.integrations.baseten.constants import BASETEN_MODEL_DEPLOYER_FLAVOR

class BasetenIntegration(Integration):
    """Definition of Baseten integration for ZenML."""

    NAME = BASETEN
    REQUIREMENTS = ["truss", "requests"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """List of flavors for the Baseten integration.
        
        Returns:
            List of flavors.
        """
        return [BasetenModelDeployerFlavor]
