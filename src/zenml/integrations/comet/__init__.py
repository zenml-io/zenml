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
"""Initialization for the Comet integration.

The CometML integrations currently enables you to use Comet tracking as a
convenient way to visualize your experiment runs within the Comet ui.
"""
from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import COMET
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

COMET_EXPERIMENT_TRACKER_FLAVOR = "comet"


class CometIntegration(Integration):
    """Definition of Comet integration for ZenML."""

    NAME = COMET
    REQUIREMENTS = ["comet-ml>=3.0.0"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Comet integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.comet.flavors import (
            CometExperimentTrackerFlavor,
        )

        return [CometExperimentTrackerFlavor]

