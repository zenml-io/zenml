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

The Deepchecks integration provides a way to validate your data in your
pipelines. It includes a way to detect data anomalies and define checks to
ensure quality of data.

The integration includes custom materializers to store and visualize Deepchecks
`SuiteResults`.
"""

from typing import List, Type, Optional

from zenml.integrations.constants import DEEPCHECKS, PANDAS
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

DEEPCHECKS_DATA_VALIDATOR_FLAVOR = "deepchecks"


class DeepchecksIntegration(Integration):
    """Definition of [Deepchecks](https://github.com/deepchecks/deepchecks) integration for ZenML."""

    NAME = DEEPCHECKS
    REQUIREMENTS = [
        "deepchecks[vision]>=0.18.0",
        "torchvision>=0.14.0",
        "opencv-python==4.5.5.64",  # pin to same version
        "opencv-python-headless==4.5.5.64",  # pin to same version
        "tenacity!=8.4.0",  # https://github.com/jd/tenacity/issues/471
        # TODO: Fix the explanation here
        # Normally, the deepchecks integrations requires pandas to work.
        # However, their version 0.8.0 is using a pandas function which got
        # removed at pandas 2.1.0. Until we can upgrade the deepchecks
        # requirement, we have to limit pandas to <2.1.0.
        "pandas<2.2.0",
    ]

    APT_PACKAGES = ["ffmpeg", "libsm6", "libxext6"]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["pandas", "torchvision", "tenacity"]

    @classmethod
    def activate(cls) -> None:
        """Activate the Deepchecks integration."""
        from zenml.integrations.deepchecks import materializers  # noqa

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.

        Returns:
            A list of requirements.
        """
        from zenml.integrations.pandas import PandasIntegration

        return cls.REQUIREMENTS + \
            PandasIntegration.get_requirements(target_os=target_os)

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
