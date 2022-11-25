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
"""Initialization for the wandb integration.

The wandb integrations currently enables you to use wandb tracking as a
convenient way to visualize your experiment runs within the wandb ui.
"""
from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import WANDB
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

WANDB_EXPERIMENT_TRACKER_FLAVOR = "wandb"


class WandbIntegration(Integration):
    """Definition of Plotly integration for ZenML."""

    NAME = WANDB
    REQUIREMENTS = ["wandb>=0.12.12", "Pillow>=9.1.0"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Weights and Biases integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.wandb.flavors import (
            WandbExperimentTrackerFlavor,
        )

        return [WandbExperimentTrackerFlavor]


WandbIntegration.check_installation()
