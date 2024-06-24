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
"""Deepchecks integration for ZenML.

The Deepchecks integration provides a way to validate your data in your pipelines.
It includes a way to detect data anomalies and define checks to ensure quality of
data.

The integration includes custom materializers to store and visualize Deepchecks
`SuiteResults`.
"""

import sys
from typing import List, Optional, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import DEEPCHECKS
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

DEEPCHECKS_DATA_VALIDATOR_FLAVOR = "deepchecks"


class DeepchecksIntegration(Integration):
    """Definition of [Deepchecks](https://github.com/deepchecks/deepchecks) integration for ZenML."""

    NAME = DEEPCHECKS
    REQUIREMENTS = []
    APT_PACKAGES = ["ffmpeg", "libsm6", "libxext6"]

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Defines platform specific requirements for the integration.

        Args:
            target_os: The target operating system.

        Returns:
            A list of requirements.
        """
        requirements = []
        # TODO: simplify once skypilot supports 3.12
        if sys.version_info.minor != 12:
            requirements = [
                "deepchecks[vision]==0.8.0",
                "torchvision>=0.14.0",
                "pandas<2.0.0",
                "opencv-python==4.5.5.64",  # pin to same version
                "opencv-python-headless==4.5.5.64",  # pin to same version
                "tenacity!=8.4.0",  # https://github.com/jd/tenacity/issues/471
            ]

        return requirements

    @staticmethod
    def activate() -> None:
        """Activate the Deepchecks integration."""
        from zenml.integrations.deepchecks import materializers  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Deepchecks integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.deepchecks.flavors import (
            DeepchecksDataValidatorFlavor,
        )

        return [DeepchecksDataValidatorFlavor]


DeepchecksIntegration.check_installation()
