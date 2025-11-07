#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Initialization for the ZenML Notion integration.

The Notion integration enables you to use Notion as a model registry to track
model metadata and versions in Notion databases.
"""

from typing import List, Type

from zenml.integrations.constants import NOTION
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

NOTION_MODEL_REGISTRY_FLAVOR = "notion"


class NotionIntegration(Integration):
    """Definition of Notion integration for ZenML."""

    NAME = NOTION

    REQUIREMENTS = [
        "notion-client>=2.0.0",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Notion integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.notion.flavors import (
            NotionModelRegistryFlavor,
        )

        return [
            NotionModelRegistryFlavor,
        ]


NotionIntegration.check_installation()

