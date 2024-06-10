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

from abc import ABC, abstractmethod
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Type,
)

from pydantic import BaseModel

from zenml.enums import PluginType
from zenml.event_hub.base_event_hub import BaseEventHub
from zenml.event_sources.base_event import BaseEvent
from zenml.logger import get_logger
from zenml.models import (
    EventSourceFlavorResponse,
    EventSourceFlavorResponseBody,
    EventSourceFlavorResponseMetadata,
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
)
from zenml.plugins.base_plugin_flavor import (
    BasePlugin,
    BasePluginConfig,
    BasePluginFlavor,
)

logger = get_logger(__name__)

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

        Returns:
            Whether the filter matches the event.
        """


# -------------------- Event Source -----------------------------


class BaseEventSourceHandler(BasePlugin, ABC):
    """Base event source handler implementation.

    This class provides a base implementation for event source handlers.

    The base event source handler acts as an intermediary between the REST API
    endpoints and the ZenML store for all operations related to event sources.
    It implements all operations related creating, updating, deleting, and
    fetching event sources from the database. It also provides a set of methods
    that can be overridden by concrete event source handlers that need to
    react to or participate in the lifecycle of an event source:

    * `_validate_event_source_request`: validate and/or modify an event source
    before it is created (before it is persisted in the database)
    * `_process_event_source_request`: react to a new event source being created
    (after it is persisted in the database)
    * `_validate_event_source_update`: validate and/or modify an event source
    update before it is applied (before the update is saved in the database)
    * `_process_event_source_update`: react to an event source being updated
    (after the update is saved in the database)
    * `_process_event_source_delete`: react to an event source being deleted
    (before it is deleted from the database)
    * `_process_event_source_response`: modify an event source before it is
    returned to the user

    In addition to optionally overriding these methods, every event source
    handler must define and provide configuration classes for the event source
    and the event filter. These are used to validate and instantiate the
    configuration from the user requests.

    Finally, since event source handlers are also sources of events, the base
    class provides methods that implementations can use to dispatch events to
    the central event hub where they can be processed and eventually trigger
    actions.
    """

    _event_hub: Optional[BaseEventHub] = None

    def __init__(self, event_hub: Optional[BaseEventHub] = None) -> None:
        """Event source handler initialization.

        Args:
            event_hub: Optional event hub to use to initialize the event source
                handler. If not set during initialization, it may be set
                at a later time by calling `set_event_hub`. An event hub must
                be configured before the event handler needs to dispatch events.
        """
        super().__init__()
        if event_hub is None:
            from zenml.event_hub.event_hub import (
                event_hub as default_event_hub,
            )

            # TODO: for now, we use the default internal event hub. In
            # the future, this should be configurable.
            event_hub = default_event_hub

        self.set_event_hub(event_hub)

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

    @property
    @abstractmethod
    def flavor_class(self) -> "Type[BaseEventSourceFlavor]":
        """Returns the flavor class of the plugin.

        Returns:
            The flavor class of the plugin.
        """

    @property
    def event_hub(self) -> BaseEventHub:
        """Get the event hub used to dispatch events.

        Returns:
            The event hub.

        Raises:
            RuntimeError: if an event hub isn't configured.
        """
        if self._event_hub is None:
            raise RuntimeError(
                f"An event hub is not configured for the "
                f"{self.flavor_class.FLAVOR} {self.flavor_class.SUBTYPE} "
                f"event source handler."
            )

        return self._event_hub

    def set_event_hub(self, event_hub: BaseEventHub) -> None:
        """Configure an event hub for this event source plugin.

        Args:
            event_hub: Event hub to be used by this event handler to dispatch
                events.
        """
        self._event_hub = event_hub

    def create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Process an event source request and create the event source in the database.

        Args:
            event_source: Event source request.

        Returns:
            The created event source.

        # noqa: DAR401
        """
        # Validate and instantiate the configuration from the request
        config = self.validate_event_source_configuration(
            event_source.configuration
        )
        # Call the implementation specific method to validate the request
        # before it is sent to the database
        self._validate_event_source_request(
            event_source=event_source, config=config
        )
        # Serialize the configuration back into the request
        event_source.configuration = config.model_dump(exclude_none=True)
        # Create the event source in the database
        event_source_response = self.zen_store.create_event_source(
            event_source=event_source
        )
        try:
            # Instantiate the configuration from the response
            config = self.validate_event_source_configuration(
                event_source.configuration
            )
            # Call the implementation specific method to process the created
            # event source
            self._process_event_source_request(
                event_source=event_source_response, config=config
            )
        except Exception:
            # If the event source creation fails, delete the event source from
            # the database
            logger.exception(
                f"Failed to create event source {event_source_response}. "
                f"Deleting the event source."
            )
            self.zen_store.delete_event_source(
                event_source_id=event_source_response.id
            )
            raise

        # Serialize the configuration back into the response
        event_source_response.set_configuration(
            config.model_dump(exclude_none=True)
        )

        # Return the response to the user
        return event_source_response

    def update_event_source(
        self,
        event_source: EventSourceResponse,
        event_source_update: EventSourceUpdate,
    ) -> EventSourceResponse:
        """Process an event source update request and update the event source in the database.

        Args:
            event_source: The event source to update.
            event_source_update: The update to be applied to the event source.

        Returns:
            The updated event source.

        # noqa: DAR401
        """
        # Validate and instantiate the configuration from the original event
        # source
        config = self.validate_event_source_configuration(
            event_source.configuration
        )
        # Validate and instantiate the configuration from the update request
        # NOTE: if supplied, the configuration update is a full replacement
        # of the original configuration
        config_update = config
        if event_source_update.configuration is not None:
            config_update = self.validate_event_source_configuration(
                event_source_update.configuration
            )
        # Call the implementation specific method to validate the update request
        # before it is sent to the database
        self._validate_event_source_update(
            event_source=event_source,
            config=config,
            event_source_update=event_source_update,
            config_update=config_update,
        )
        # Serialize the configuration update back into the update request
        event_source_update.configuration = config_update.model_dump(
            exclude_none=True
        )

        # Update the event source in the database
        event_source_response = self.zen_store.update_event_source(
            event_source_id=event_source.id,
            event_source_update=event_source_update,
        )
        try:
            # Instantiate the configuration from the response
            response_config = self.validate_event_source_configuration(
                event_source_response.configuration
            )
            # Call the implementation specific method to process the update
            # request before it is sent to the database
            self._process_event_source_update(
                event_source=event_source_response,
                config=response_config,
                previous_event_source=event_source,
                previous_config=config,
            )
        except Exception:
            # If the event source update fails, roll back the event source in
            # the database to the original state
            logger.exception(
                f"Failed to update event source {event_source}. "
                f"Rolling back the event source to the previous state."
            )
            self.zen_store.update_event_source(
                event_source_id=event_source.id,
                event_source_update=EventSourceUpdate.from_response(
                    event_source
                ),
            )
            raise

        # Serialize the configuration back into the response
        event_source_response.set_configuration(
            response_config.model_dump(exclude_none=True)
        )
        # Return the response to the user
        return event_source_response

    def delete_event_source(
        self,
        event_source: EventSourceResponse,
        force: bool = False,
    ) -> None:
        """Process an event source delete request and delete the event source in the database.

        Args:
            event_source: The event source to delete.
            force: Whether to force delete the event source from the database
                even if the event source handler fails to delete the event
                source.

        # noqa: DAR401
        """
        # Validate and instantiate the configuration from the original event
        # source
        config = self.validate_event_source_configuration(
            event_source.configuration
        )
        try:
            # Call the implementation specific method to process the deleted
            # event source before it is deleted from the database
            self._process_event_source_delete(
                event_source=event_source,
                config=config,
                force=force,
            )
        except Exception:
            logger.exception(f"Failed to delete event source {event_source}. ")
            if not force:
                raise

            logger.warning(f"Force deleting event source {event_source}.")

        # Delete the event source from the database
        self.zen_store.delete_event_source(
            event_source_id=event_source.id,
        )

    def get_event_source(
        self, event_source: EventSourceResponse, hydrate: bool = False
    ) -> EventSourceResponse:
        """Process an event source response before it is returned to the user.

        Args:
            event_source: The event source fetched from the database.
            hydrate: Whether to hydrate the event source.

        Returns:
            The event source.
        """
        if hydrate:
            # Instantiate the configuration from the response
            config = self.validate_event_source_configuration(
                event_source.configuration
            )
            # Call the implementation specific method to process the response
            self._process_event_source_response(
                event_source=event_source, config=config
            )
            # Serialize the configuration back into the response
            event_source.set_configuration(
                config.model_dump(exclude_none=True)
            )

        # Return the response to the user
        return event_source

    def validate_event_source_configuration(
        self, event_source_config: Dict[str, Any]
    ) -> EventSourceConfig:
        """Validate and return the event source configuration.

        Args:
            event_source_config: The event source configuration to validate.

        Returns:
            The validated event source configuration.

        Raises:
            ValueError: if the configuration is invalid.
        """
        try:
            return self.config_class(**event_source_config)
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration for event source: {e}."
            ) from e

    def validate_event_filter_configuration(
        self,
        configuration: Dict[str, Any],
    ) -> EventFilterConfig:
        """Validate and return the configuration of an event filter.

        Args:
            configuration: The configuration to validate.

        Returns:
            Instantiated event filter config.

        Raises:
            ValueError: if the configuration is invalid.
        """
        try:
            return self.filter_class(**configuration)
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration for event filter: {e}."
            ) from e

    def dispatch_event(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
    ) -> None:
        """Dispatch an event to all active triggers that match the event.

        Args:
            event: The event to dispatch.
            event_source: The event source that produced the event.
        """
        self.event_hub.publish_event(
            event=event,
            event_source=event_source,
        )

    def _validate_event_source_request(
        self, event_source: EventSourceRequest, config: EventSourceConfig
    ) -> None:
        """Validate an event source request before it is created in the database.

        Concrete event source handlers should override this method to add
        implementation specific functionality pertaining to the validation of
        a new event source. The implementation may also modify the event source
        request and/or configuration in place to apply implementation specific
        changes before the request is stored in the database.

        If validation is required, the implementation should raise a
        ValueError if the configuration is invalid. If any exceptions are raised
        during the validation, the event source will not be created in the
        database.

        The resulted configuration is serialized back into the event source
        request before it is stored in the database.

        The implementation should not use this method to provision any external
        resources, as the event source may not be created in the database if
        the database level validation fails.

        Args:
            event_source: Event source request.
            config: Event source configuration instantiated from the request.
        """
        pass

    def _process_event_source_request(
        self, event_source: EventSourceResponse, config: EventSourceConfig
    ) -> None:
        """Process an event source request after it is created in the database.

        Concrete event source handlers should override this method to add
        implementation specific functionality pertaining to the creation of
        a new event source. The implementation may also modify the event source
        response and/or configuration in place to apply implementation specific
        changes before the response is returned to the user.

        The resulted configuration is serialized back into the event source
        response before it is returned to the user.

        The implementation should use this method to provision any external
        resources required for the event source. If any of the provisioning
        fails, the implementation should raise an exception and the event source
        will be deleted from the database.

        Args:
            event_source: Newly created event source
            config: Event source configuration instantiated from the response.
        """
        pass

    def _validate_event_source_update(
        self,
        event_source: EventSourceResponse,
        config: EventSourceConfig,
        event_source_update: EventSourceUpdate,
        config_update: EventSourceConfig,
    ) -> None:
        """Validate an event source update before it is reflected in the database.

        Concrete event source handlers should override this method to add
        implementation specific functionality pertaining to validation of an
        event source update request. The implementation may also modify the
        event source update and/or configuration update in place to apply
        implementation specific changes.

        If validation is required, the implementation should raise a
        ValueError if the configuration update is invalid. If any exceptions are
        raised during the validation, the event source will not be updated in
        the database.

        The resulted configuration update is serialized back into the event
        source update before it is stored in the database.

        The implementation should not use this method to provision any external
        resources, as the event source may not be updated in the database if
        the database level validation fails.

        Args:
            event_source: Original event source before the update.
            config: Event source configuration instantiated from the original
                event source.
            event_source_update: Event source update request.
            config_update: Event source configuration instantiated from the
                updated event source.
        """
        pass

    def _process_event_source_update(
        self,
        event_source: EventSourceResponse,
        config: EventSourceConfig,
        previous_event_source: EventSourceResponse,
        previous_config: EventSourceConfig,
    ) -> None:
        """Process an event source after it is updated in the database.

        Concrete event source handlers should override this method to add
        implementation specific functionality pertaining to updating an existing
        event source. The implementation may also modify the event source
        and/or configuration in place to apply implementation specific
        changes before the response is returned to the user.

        The resulted configuration is serialized back into the event source
        response before it is returned to the user.

        The implementation should use this method to provision any external
        resources required for the event source update. If any of the
        provisioning fails, the implementation should raise an exception and the
        event source will be rolled back to the previous state in the database.

        Args:
            event_source: Event source after the update.
            config: Event source configuration instantiated from the updated
                event source.
            previous_event_source: Original event source before the update.
            previous_config: Event source configuration instantiated from the
                original event source.
        """
        pass

    def _process_event_source_delete(
        self,
        event_source: EventSourceResponse,
        config: EventSourceConfig,
        force: Optional[bool] = False,
    ) -> None:
        """Process an event source before it is deleted from the database.

        Concrete event source handlers should override this method to add
        implementation specific functionality pertaining to the deletion of an
        event source.

        The implementation should use this method to deprovision any external
        resources required for the event source. If any of the deprovisioning
        fails, the implementation should raise an exception and the
        event source will kept in the database (unless force is True, in which
        case the event source will be deleted from the database regardless of
        any deprovisioning failures).

        Args:
            event_source: Event source before the deletion.
            config: Validated instantiated event source configuration before
                the deletion.
            force: Whether to force deprovision the event source.
        """
        pass

    def _process_event_source_response(
        self, event_source: EventSourceResponse, config: EventSourceConfig
    ) -> None:
        """Process an event source response before it is returned to the user.

        Concrete event source handlers should override this method to add
        implementation specific functionality pertaining to how the event source
        response is returned to the user. The implementation may modify the
        the event source response and/or configuration in place.

        The resulted configuration is serialized back into the event source
        response before it is returned to the user.

        This method is applied to all event source responses fetched from the
        database before they are returned to the user, with the exception of
        those returned from the `create_event_source`, `update_event_source`,
        and `delete_event_source` methods, which have their own specific
        processing methods.

        Args:
            event_source: Event source response.
            config: Event source configuration instantiated from the response.
        """
        pass


# -------------------- Flavors ----------------------------------


class BaseEventSourceFlavor(BasePluginFlavor, ABC):
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
        return cls.EVENT_SOURCE_CONFIG_CLASS.model_json_schema()

    @classmethod
    def get_event_source_config_schema(cls) -> Dict[str, Any]:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        return cls.EVENT_FILTER_CONFIG_CLASS.model_json_schema()

    @classmethod
    def get_flavor_response_model(
        cls, hydrate: bool
    ) -> EventSourceFlavorResponse:
        """Convert the Flavor into a Response Model.

        Args:
            hydrate: Whether the model should be hydrated.

        Returns:
            The Flavor Response model for the Event Source implementation
        """
        metadata = None
        if hydrate:
            metadata = EventSourceFlavorResponseMetadata(
                source_config_schema=cls.get_event_source_config_schema(),
                filter_config_schema=cls.get_event_filter_config_schema(),
            )
        return EventSourceFlavorResponse(
            body=EventSourceFlavorResponseBody(),
            metadata=metadata,
            name=cls.FLAVOR,
            type=cls.TYPE,
            subtype=cls.SUBTYPE,
        )
