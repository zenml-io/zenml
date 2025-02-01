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
"""Initialization of the Baseten integration for ZenML.

The Baseten integration allows you to use the Baseten model serving
to implement continuous model deployment.
"""
from typing import List, Type

from zenml.integrations.constants import BASETEN
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

BASETEN_MODEL_DEPLOYER_FLAVOR = "baseten"


class BasetenIntegration(Integration):
    """Definition of Baseten integration for ZenML."""

    NAME = BENTOML
    REQUIREMENTS = [
        "baseten>=0.8.2,<1.0.0",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activate the Baseten integration."""
        from zenml.integrations.baseten import materializers  # noqa
        from zenml.integrations.baseten import model_deployers  # noqa
        from zenml.integrations.baseten import services  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for BentoML.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.baseten.flavors import (
            BasetenModelDeployerFlavor,
        )

        return [BasetenModelDeployerFlavor]


BasetenIntegration.check_installation()
