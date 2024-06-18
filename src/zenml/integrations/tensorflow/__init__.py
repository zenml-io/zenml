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
"""Initialization for TensorFlow integration."""

import platform
import sys
from typing import List, Optional
from zenml.integrations.constants import TENSORFLOW
from zenml.integrations.integration import Integration


class TensorflowIntegration(Integration):
    """Definition of Tensorflow integration for ZenML."""

    NAME = TENSORFLOW
    REQUIREMENTS = []

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        # need to import this explicitly to load the Tensorflow file IO support
        # for S3 and other file systems
        if not platform.system() == "Darwin" or not platform.machine() == "arm64":
            import tensorflow_io  # type: ignore

        from zenml.integrations.tensorflow import materializers  # noqa

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Defines platform specific requirements for the integration.

        Args:
            target_os: The target operating system.

        Returns:
            A list of requirements.
        """
        target_os = target_os or platform.system()
        requirements = [
            "typing-extensions>=4.6.1",
        ]
        if sys.version_info.minor == 8:
            requirements.append("tensorflow==2.12")
            requirements.append("tensorflow-io==0.31.0")
        else:
            requirements.append("tensorflow>=2.12,<=2.15")
        if not (target_os == "Darwin" or platform.machine() == "arm64"):
            requirements.append("tensorflow_io>=0.24.0")
        return requirements


TensorflowIntegration.check_installation()
