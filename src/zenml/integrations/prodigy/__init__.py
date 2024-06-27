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
"""Initialization of the Prodigy integration."""
from typing import List, Type

from zenml.integrations.constants import PRODIGY
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

PRODIGY_ANNOTATOR_FLAVOR = "prodigy"


class ProdigyIntegration(Integration):
    """Definition of Prodigy integration for ZenML."""

    NAME = PRODIGY
    REQUIREMENTS = [
        "prodigy",
        "urllib3<2",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Prodigy integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.prodigy.flavors import (
            ProdigyAnnotatorFlavor,
        )

        return [ProdigyAnnotatorFlavor]


ProdigyIntegration.check_installation()
