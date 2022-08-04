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
"""Initialization of the DVC integration.

The DVC integration allows the use of cloud artifact stores and file
operations on DVC buckets.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import DVC
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

DVC_ARTIFACT_STORE_FLAVOR = "dvc"


class DVCIntegration(Integration):
    """Definition of DVC integration for ZenML."""

    NAME = DVC
    REQUIREMENTS = ["dvc"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the dvc integration.

        Returns:
            List of stack component flavors for this integration.
        """
        return [
            FlavorWrapper(
                name=DVC_ARTIFACT_STORE_FLAVOR,
                source="zenml.integrations.dvc.artifact_stores.DVCArtifactStore",
                type=StackComponentType.ARTIFACT_STORE,
                integration=cls.NAME,
            )
        ]


DVCIntegration.check_installation()
