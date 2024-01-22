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
"""Module containing Neptune integration."""

from typing import List, Type

from zenml.integrations.constants import NEPTUNE
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

# This is the flavor that will be used when registering this stack component
#  `zenml experiment_tracker register ... -f neptune`
NEPTUNE_MODEL_EXPERIMENT_TRACKER_FLAVOR = "neptune"


# Create a Subclass of the Integration Class
class NeptuneIntegration(Integration):
    """Definition of the neptune.ai integration with ZenML."""

    NAME = NEPTUNE
    REQUIREMENTS = ["neptune"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Neptune integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.neptune.flavors import (
            NeptuneExperimentTrackerFlavor,
        )

        return [
            NeptuneExperimentTrackerFlavor,
        ]


NeptuneIntegration.check_installation()  # this checks if the requirements are installed
