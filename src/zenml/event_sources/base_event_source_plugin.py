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
"""Base implementation for event sources."""
import json
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Type,
)

from pydantic import BaseModel

from zenml.enums import PluginType
from zenml.logger import get_logger
from zenml.models import (
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
)
from zenml.models.v2.plugin.event_flavor import EventFlavorResponse
from zenml.plugins.base_plugin_flavor import (
    BasePlugin,
    BasePluginConfig,
    BasePluginFlavor,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# -------------------- Event Models -----------------------------------


class BaseEvent(BaseModel):
    """Base class for all inbound events."""


# -------------------- Configuration Models ----------------------------------


class EventSourceConfig(BasePluginConfig):
    """The Event Source configuration."""


class EventFilterConfig(BaseModel, ABC):
    """The Event Filter configuration."""

    @abstractmethod
    def event_matches_filter(self, event: BaseEvent) -> bool:
        """All implementations need to implement this check.

        If the filter matches the inbound event instance, this should
        return True, else False.

        Args:
            event: The inbound event instance.

        Returns: Whether the filter matches the event.
        """


# -------------------- Plugin -----------------------------------


class BaseEventSourcePlugin(BasePlugin, ABC):
    """Implementation for an EventPlugin."""

    @property
    @abstractmethod
    def config_class(self) -> Type[EventSourceConfig]:
        """Returns the event source configuration class.

        Returns:
            The configuration.
        """

    @property
    @abstractmethod
    def filter_class(self) -> Type[EventFilterConfig]:
        """Returns the event filter configuration class.

        Returns:
            The event filter configuration class.
        """

    def create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method for plugin specific functionality.

        All implementation of the BaseEventSource can overwrite this method to add
        implementation specific functionality.

        Args:
            event_source: Request model for the event source.

        Returns:
            The created event source.
        """
        self.validate_event_source_configuration(event_source.configuration)
        return self._create_event_source(event_source=event_source)

    def update_event_source(
        self,
        event_source_id: UUID,
        event_source_update: EventSourceUpdate,
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method for plugin specific functionality.

        All implementation of the BaseEventSource can overwrite this method to add
        implementation specific functionality.

        Args:
            event_source_id: The ID of the event_source to update.
            event_source_update: The update to be applied to the event_source.

        Returns:
            The created event source.
        """
        return self._update_event_source(
            event_source_id=event_source_id,
            event_source_update=event_source_update,
        )

    @abstractmethod
    def _update_event_source(
        self,
        event_source_id: UUID,
        event_source_update: EventSourceUpdate,
    ) -> EventSourceResponse:
        """Wraps the zen_store update method to add plugin specific functionality.

        Args:
            event_source_id: The ID of the event_source to update.
            event_source_update: The update to be applied to the event_source.

        Returns:
            The event source response body.
        """

    @abstractmethod
    def _create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method for plugin specific functionality.

        All implementation of the BaseEventSource can overwrite this method to add
        implementation specific functionality.

        Args:
            event_source: Request model for the event source.

        Returns:
            The created event source.
        """

    def validate_event_source_configuration(
        self, event_source_config: Dict[str, Any]
    ) -> None:
        """Validates the event source configuration.

        Args:
            event_source_config: The event source configuration to validate.

        Raises:
            ValueError: if the configuration is invalid.
        """
        try:
            self.config_class(**event_source_config)
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration for event source: {e}."
            ) from e

    def validate_event_filter_configuration(
        self,
        configuration: Dict[str, Any],
    ) -> None:
        """Validate the configuration of an event filter.

        Args:
            configuration: The configuration to validate.

        Raises:
            ValueError: if the configuration is invalid.
        """
        try:
            self.filter_class(**configuration)
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration for event filter: {e}."
            ) from e


# -------------------- Flavors ----------------------------------


class BaseEventSourcePluginFlavor(BasePluginFlavor, ABC):
    """Base Event Plugin Flavor to access an event plugin along with its configurations."""

    TYPE: ClassVar[PluginType] = PluginType.EVENT_SOURCE

    # EventPlugin specific
    EVENT_SOURCE_CONFIG_CLASS: ClassVar[Type[EventSourceConfig]]
    EVENT_FILTER_CONFIG_CLASS: ClassVar[Type[EventFilterConfig]]

    @classmethod
    def get_event_filter_config_schema(cls) -> Dict[str, Any]:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        config_schema: Dict[str, Any] = json.loads(
            cls.EVENT_SOURCE_CONFIG_CLASS.schema_json()
        )

        return config_schema

    @classmethod
    def get_event_source_config_schema(cls) -> Dict[str, Any]:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        config_schema: Dict[str, Any] = json.loads(
            cls.EVENT_FILTER_CONFIG_CLASS.schema_json()
        )

        return config_schema

    @classmethod
    def get_plugin_flavor_response_model(cls) -> EventFlavorResponse:
        """Convert the Flavor into a Response Model."""
        return EventFlavorResponse(
            flavor_name=cls.FLAVOR,
            plugin_type=cls.TYPE,
            plugin_subtype=cls.SUBTYPE,
            source_config_schema=cls.get_event_source_config_schema(),
            filter_config_schema=cls.get_event_filter_config_schema(),
        )
