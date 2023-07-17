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
"""Initialization of the KServe integration for ZenML.

The KServe integration allows you to use the KServe model serving
platform to implement continuous model deployment.
"""
from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import KSERVE
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

KSERVE_MODEL_DEPLOYER_FLAVOR = "kserve"


class KServeIntegration(Integration):
    """Definition of KServe integration for ZenML."""

    NAME = KSERVE
    REQUIREMENTS = [
        "kserve>=0.9.0,<=10",
        "torch-model-archiver",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activate the KServe integration."""
        from zenml.integrations.kserve import model_deployers  # noqa
        from zenml.integrations.kserve import secret_schemas  # noqa
        from zenml.integrations.kserve import services  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for KServe.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.kserve.flavors import KServeModelDeployerFlavor

        return [KServeModelDeployerFlavor]


KServeIntegration.check_installation()
