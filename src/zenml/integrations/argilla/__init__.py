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
"""Initialization of the Argilla integration."""
from typing import List, Type

from zenml.integrations.constants import ARGILLA
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

ARGILLA_ANNOTATOR_FLAVOR = "argilla"


class ArgillaIntegration(Integration):
    """Definition of Argilla integration for ZenML."""

    NAME = ARGILLA
    REQUIREMENTS = [
        "argilla>=2.0.0",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Argilla integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.argilla.flavors import (
            ArgillaAnnotatorFlavor,
        )

        return [ArgillaAnnotatorFlavor]


ArgillaIntegration.check_installation()
