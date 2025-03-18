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
"""Initialization for TensorBoard integration."""

from typing import List, Optional
from zenml.integrations.constants import TENSORBOARD
from zenml.integrations.integration import Integration


class TensorBoardIntegration(Integration):
    """Definition of TensorBoard integration for ZenML."""

    NAME = TENSORBOARD
    REQUIREMENTS = []

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Defines platform specific requirements for the integration.

        Args:
            target_os: The target operating system.

        Returns:
            A list of requirements.
        """
        requirements = ["tensorboard>=2.12,<2.15"]
        return requirements

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.tensorboard import services  # noqa

