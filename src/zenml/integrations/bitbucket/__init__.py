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
"""Initialization of the bitbucket ZenML integration."""
from typing import List, Type

from zenml.integrations.constants import BITBUCKET
from zenml.integrations.integration import Integration
from zenml.plugins.base_plugin_flavor import BasePluginFlavor

BITBUCKET_EVENT_FLAVOR = "bitbucket"


class BitbucketIntegration(Integration):
    """Definition of bitbucket integration for ZenML."""

    NAME = BITBUCKET
    REQUIREMENTS: List[str] = []

    @classmethod
    def plugin_flavors(cls) -> List[Type[BasePluginFlavor]]:
        """Declare the event flavors for the bitbucket integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.bitbucket.plugins import BitbucketWebhookEventSourceFlavor

        return [BitbucketWebhookEventSourceFlavor]

