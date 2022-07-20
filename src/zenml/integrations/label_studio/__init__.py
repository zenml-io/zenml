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
"""Initialization of the Label Studio integration."""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import LABEL_STUDIO
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

LABEL_STUDIO_ANNOTATOR_FLAVOR = "label_studio"


class LabelStudioIntegration(Integration):
    """Definition of Label Studio integration for ZenML."""

    NAME = LABEL_STUDIO
    REQUIREMENTS = ["label-studio", "label-studio-sdk"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Label Studio integration.

        Returns:
            List of stack component flavors for this integration.
        """
        return [
            FlavorWrapper(
                name=LABEL_STUDIO_ANNOTATOR_FLAVOR,
                source="zenml.integrations.label_studio.annotators.LabelStudioAnnotator",
                type=StackComponentType.ANNOTATOR,
                integration=cls.NAME,
            ),
        ]


LabelStudioIntegration.check_installation()
