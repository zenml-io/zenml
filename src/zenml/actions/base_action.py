#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Base implementation of actions."""
import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Type

from zenml.enums import PluginType
from zenml.models.v2.plugin.action_flavor import ActionFlavorResponse
from zenml.plugins.base_plugin_flavor import (
    BasePlugin,
    BasePluginConfig,
    BasePluginFlavor,
)

# -------------------- Configuration Models ----------------------------------


class ActionConfig(BasePluginConfig):
    """Allows configuring the action configuration."""


# -------------------- Plugin -----------------------------------


class BaseActionHandler(BasePlugin, ABC):
    """Implementation for an action handler."""

    @property
    @abstractmethod
    def config_class(self) -> Type[ActionConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """


# -------------------- Flavors ---------------------------------------------


class BaseActionFlavor(BasePluginFlavor, ABC):
    """Base Action Flavor to register Action Configurations."""

    TYPE: ClassVar[PluginType] = PluginType.ACTION

    # Action specific
    ACTION_CONFIG_CLASS: ClassVar[Type[ActionConfig]]

    @classmethod
    def get_action_config_schema(cls) -> Dict[str, Any]:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        config_schema: Dict[str, Any] = json.loads(
            cls.ACTION_CONFIG_CLASS.schema_json()
        )
        return config_schema

    @classmethod
    def to_model(self) -> ActionFlavorResponse:
        """Convert the Flavor into a Flavor Response Model."""
        return ActionFlavorResponse(
            name=self.FLAVOR,
            config_schema=self.get_action_config_schema(),
        )
