#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Deepchecks integration for ZenML.

The Deepchecks integration provides a way to validate your data in your pipelines.
It includes a way to detect data anomalies and define checks to ensure quality of
data.

The integration includes custom materializers to store Deepchecks `SuiteResults` and
a visualizer to visualize the results in an easy way on a notebook and in your
browser.
"""

from typing import List, Type, TYPE_CHECKING

from zenml.integrations.constants import (
    DEEPCHECKS,
    DEEPCHECKS_TABULAR,
    DEEPCHECKS_VISION,
)
from zenml.integrations.integration import Integration

if TYPE_CHECKING:
    from zenml.stack import Flavor

DEEPCHECKS_DATA_VALIDATOR_FLAVOR = "deepchecks"
DEEPCHECKS_TABULAR_DATA_VALIDATOR_FLAVOR = "deepchecks-tabular"
DEEPCHECKS_VISION_DATA_VALIDATOR_FLAVOR = "deepchecks-vision"


class BaseDeepchecksIntegration(Integration):
    """Base class for Deepchecks integrations.

    Activates materializers and visualizers so that they can be used with any
    Deepchecks flavor.
    """

    @staticmethod
    def activate() -> None:
        """Activate the Deepchecks integration."""
        from zenml.integrations.deepchecks import materializers  # noqa
        from zenml.integrations.deepchecks import visualizers  # noqa


class DeepchecksTabularIntegration(BaseDeepchecksIntegration):
    """Definition of [Deepchecks](https://github.com/deepchecks/deepchecks) integration for ZenML."""

    NAME = DEEPCHECKS_TABULAR
    REQUIREMENTS = ["deepchecks==0.8.0"]

    @classmethod
    def flavors(cls) -> List[Type["Flavor"]]:
        """Declare the stack component flavors for the Deepchecks integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.deepchecks.flavors.deepchecks_tabular_data_validator_flavor import (
            DeepchecksTabularDataValidatorFlavor,
        )

        return [DeepchecksTabularDataValidatorFlavor]


class DeepchecksVisionIntegration(BaseDeepchecksIntegration):
    """Definition of the Deepchecks Tabular integration for ZenML."""

    NAME = DEEPCHECKS_VISION
    REQUIREMENTS = ["deepchecks[vision]==0.8.0", "torchvision==0.14.0"]
    APT_PACKAGES = ["ffmpeg", "libsm6", "libxext6"]

    @classmethod
    def flavors(cls) -> List[Type["Flavor"]]:
        """Declare the stack component flavors for the Deepchecks integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.deepchecks.flavors.deepchecks_vision_data_validator_flavor import (
            DeepchecksVisionDataValidatorFlavor,
        )

        return [DeepchecksVisionDataValidatorFlavor]


class DeprecatedDeepchecksIntegration(DeepchecksVisionIntegration):
    """Old Deepchecks integration for backwards compatibility."""

    NAME = DEEPCHECKS

    @classmethod
    def flavors(cls) -> List[Type["Flavor"]]:
        """Declare the stack component flavors for the Deepchecks integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor import (
            DeepchecksDataValidatorFlavor,
        )

        return [DeepchecksDataValidatorFlavor]

    # TODO: how to throw a deprecation warning when installing this?


DeepchecksTabularIntegration.check_installation()
DeepchecksVisionIntegration.check_installation()
DeprecatedDeepchecksIntegration.check_installation()
