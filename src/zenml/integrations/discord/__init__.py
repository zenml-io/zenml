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
"""Discord integration for alerter components."""

from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import DISCORD
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

DISCORD_ALERTER_FLAVOR = "discord"


class DiscordIntegration(Integration):
    """Definition of a Discord integration for ZenML.

    Implemented using [Discord API Wrapper](https://pypi.org/project/discord.py/).
    """

    NAME = DISCORD
    REQUIREMENTS = ["discord.py>=2.3.2", "aiohttp>=3.8.1", "asyncio"]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["aiohttp","asyncio"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Discord integration.

        Returns:
            List of new flavors defined by the Discord integration.
        """
        from zenml.integrations.discord.flavors import DiscordAlerterFlavor

        return [DiscordAlerterFlavor]


DiscordIntegration.check_installation()
