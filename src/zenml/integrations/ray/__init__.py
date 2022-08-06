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
"""Initialization for Ray integration.

The Ray integrations offers a variety of ways to use the awesome Ray eco-system 
of libraries with ZenML.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import FEAST
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

FEAST_FEATURE_STORE_FLAVOR = "feast"


class RayIntegration(Integration):
    """Definition of Ray integration for ZenML."""

    NAME = FEAST
    REQUIREMENTS = ["ray~=1.13.0"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Ray integration.

        Returns:
            List of stack component flavors for this integration.
        """
        return [
            FlavorWrapper(
                name=FEAST_FEATURE_STORE_FLAVOR,
                source="zenml.integrations.feast.feature_stores.FeastFeatureStore",
                type=StackComponentType.FEATURE_STORE,
                integration=cls.NAME,
            )
        ]


RayIntegration.check_installation()
