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
"""Initialization of the Evidently integration.

The Evidently integration provides a way to monitor your models in production.
It includes a way to detect data drift and different kinds of model performance
issues.

The results of Evidently calculations can either be exported as an interactive
dashboard (visualized as an html file or in your Jupyter notebook), or as a JSON
file.
"""

from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import EVIDENTLY
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

EVIDENTLY_DATA_VALIDATOR_FLAVOR = "evidently"


class EvidentlyIntegration(Integration):
    """[Evidently](https://github.com/evidentlyai/evidently) integration for ZenML."""

    NAME = EVIDENTLY
    REQUIREMENTS = ["evidently==0.1.54dev0"]

    @staticmethod
    def activate() -> None:
        """Activate the Deepchecks integration."""
        from zenml.integrations.evidently import materializers  # noqa
        from zenml.integrations.evidently import visualizers  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Great Expectations integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.evidently.flavors import (
            EvidentlyDataValidatorFlavor,
        )

        return [EvidentlyDataValidatorFlavor]


EvidentlyIntegration.check_installation()
