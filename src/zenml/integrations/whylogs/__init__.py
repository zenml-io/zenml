#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Initialization of the whylogs integration."""

from typing import List, Type, Optional

from zenml.integrations.constants import WHYLOGS
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

WHYLOGS_DATA_VALIDATOR_FLAVOR = "whylogs"


class WhylogsIntegration(Integration):
    """Definition of [whylogs](https://github.com/whylabs/whylogs) integration for ZenML."""

    NAME = WHYLOGS
    REQUIREMENTS = ["whylogs[viz]~=1.0.5", "whylogs[whylabs]~=1.0.5"]

    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["pandas"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.whylogs import materializers  # noqa
        from zenml.integrations.whylogs import secret_schemas  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Great Expectations integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.whylogs.flavors import (
            WhylogsDataValidatorFlavor,
        )

        return [WhylogsDataValidatorFlavor]

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None, python_version: Optional[str] = None
    ) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.
            python_version: The Python version to use for the requirements.

        Returns:
            A list of requirements.
        """
        from zenml.integrations.pandas import PandasIntegration

        return cls.REQUIREMENTS + \
            PandasIntegration.get_requirements(target_os=target_os, python_version=python_version)


