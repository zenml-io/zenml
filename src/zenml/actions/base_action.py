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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Type

from zenml.enums import PluginType
from zenml.models import (
    ActionFlavorResponse,
    ActionFlavorResponseBody,
    ActionFlavorResponseMetadata,
    TriggerExecutionResponse,
)
from zenml.plugins.base_plugin_flavor import (
    BasePlugin,
    BasePluginConfig,
    BasePluginFlavor,
)

if TYPE_CHECKING:
    from zenml.zen_server.rbac.models import Resource


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

    @abstractmethod
    def run(
        self,
        config: Dict[str, Any],
        trigger_execution: TriggerExecutionResponse,
    ) -> None:
        """Method that executes the configured action.

        Args:
            config: The action configuration
            trigger_execution: The trigger_execution object from the database
        """
        pass

    @abstractmethod
    def extract_resources(
        self,
        action_config: ActionConfig,
    ) -> List["Resource"]:
        """Extract related resources for this action."""

    def validate_and_action_configuration(
        self, event_source_config: Dict[str, Any]
    ) -> ActionConfig:
        """Validates the action configuration.

        Args:
            event_source_config: The action configuration to validate.

        Raises:
            ValueError: if the configuration is invalid.
        """
        try:
            return self.config_class(**event_source_config)
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration for event source: {e}."
            ) from e


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
    def get_flavor_response_model(cls, hydrate: bool) -> ActionFlavorResponse:
        """Convert the Flavor into a Response Model.

        Args:
            hydrate: Whether the model should be hydrated.
        """
        metadata = None
        if hydrate:
            metadata = ActionFlavorResponseMetadata(
                config_schema=cls.get_action_config_schema(),
            )
        return ActionFlavorResponse(
            body=ActionFlavorResponseBody(),
            metadata=metadata,
            name=cls.FLAVOR,
            type=cls.TYPE,
            subtype=cls.SUBTYPE,
        )
