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
from typing import Any, ClassVar, Dict, Optional, Type

from zenml.enums import PluginType
from zenml.event_hub.base_event_hub import BaseEventHub
from zenml.logger import get_logger
from zenml.models import (
    ActionFlavorResponse,
    ActionFlavorResponseBody,
    ActionFlavorResponseMetadata,
    TriggerExecutionResponse,
    TriggerRequest,
    TriggerResponse,
    TriggerUpdate,
)
from zenml.models.v2.base.base import BaseResponse
from zenml.plugins.base_plugin_flavor import (
    BasePlugin,
    BasePluginConfig,
    BasePluginFlavor,
)
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.rbac.models import ResourceType

logger = get_logger(__name__)


# -------------------- Configuration Models ----------------------------------


class ActionConfig(BasePluginConfig):
    """Allows configuring the action configuration."""


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

        Returns:
            The response model.
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


# -------------------- Plugin -----------------------------------


class BaseActionHandler(BasePlugin, ABC):
    """Implementation for an action handler."""

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
    def config_class(self) -> Type[ActionConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """

    @property
    @abstractmethod
    def flavor_class(self) -> Type[BaseActionFlavor]:
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
                f"action handler."
            )

        return self._event_hub

    def set_event_hub(self, event_hub: BaseEventHub) -> None:
        """Configure an event hub for this event source plugin.

        Args:
            event_hub: Event hub to be used by this event handler to dispatch
                events.
        """
        self._event_hub = event_hub
        self._event_hub.subscribe_action_handler(
            action_flavor=self.flavor_class.FLAVOR,
            action_subtype=self.flavor_class.SUBTYPE,
            callback=self.event_hub_callback,
        )

    def event_hub_callback(
        self,
        config: Dict[str, Any],
        trigger_execution: TriggerExecutionResponse,
        auth_context: AuthContext,
    ) -> None:
        """Callback to be used by the event hub to dispatch events to the action handler.

        Args:
            config: The action configuration
            trigger_execution: The trigger execution
            auth_context: Authentication context with an API token that can be
                used by external workloads to authenticate with the server
                during the execution of the action. This API token is associated
                with the service account that was configured for the trigger
                that activated the action and has a validity defined by the
                trigger's authentication window.
        """
        try:
            config_obj = self.config_class(**config)
        except ValueError as e:
            logger.exception(
                f"Action handler {self.flavor_class.FLAVOR} of type "
                f"{self.flavor_class.SUBTYPE} received an invalid configuration "
                f"from the event hub: {e}."
            )
            return

        try:
            # TODO: this would be a great place to convert the event back into its
            # original form and pass it to the action handler.
            self.run(
                config=config_obj,
                trigger_execution=trigger_execution,
                auth_context=auth_context,
            )
        except Exception:
            # Don't let the event hub crash if the action handler fails
            # TODO: we might want to return a value here indicating to the event
            # hub that the action handler failed to execute the action. This can
            # be used by the event hub to retry the action handler or to log the
            # failure.
            logger.exception(
                f"Action handler {self.flavor_class.FLAVOR} of type "
                f"{self.flavor_class.SUBTYPE} failed to execute the action "
                f"with configuration {config}."
            )

    @abstractmethod
    def run(
        self,
        config: ActionConfig,
        trigger_execution: TriggerExecutionResponse,
        auth_context: AuthContext,
    ) -> None:
        """Execute an action.

        Args:
            config: The action configuration
            trigger_execution: The trigger execution
            auth_context: Authentication context with an API token that can be
                used by external workloads to authenticate with the server
                during the execution of the action. This API token is associated
                with the service account that was configured for the trigger
                that activated the action and has a validity defined by the
                trigger's authentication window.
        """

    def create_trigger(self, trigger: TriggerRequest) -> TriggerResponse:
        """Process a trigger request and create the trigger in the database.

        Args:
            trigger: Trigger request.

        Returns:
            The created trigger.

        # noqa: DAR401
        """
        # Validate and instantiate the configuration from the request
        config = self.validate_action_configuration(trigger.action)
        # Call the implementation specific method to validate the request
        # before it is sent to the database
        self._validate_trigger_request(trigger=trigger, config=config)
        # Serialize the configuration back into the request
        trigger.action = config.dict(exclude_none=True)
        # Create the trigger in the database
        trigger_response = self.zen_store.create_trigger(trigger=trigger)
        try:
            # Instantiate the configuration from the response
            config = self.validate_action_configuration(trigger.action)
            # Call the implementation specific method to process the created
            # trigger
            self._process_trigger_request(
                trigger=trigger_response, config=config
            )
            # Add any implementation specific related resources to the trigger
            # response
            self._populate_trigger_response_resources(
                trigger=trigger_response, config=config
            )
            # Activate the trigger in the event hub to effectively start
            # dispatching events to the action handler
            self.event_hub.activate_trigger(trigger=trigger_response)
        except Exception:
            # If the trigger creation fails, delete the trigger from
            # the database
            logger.exception(
                f"Failed to create trigger {trigger_response}. "
                f"Deleting the trigger."
            )
            self.zen_store.delete_trigger(trigger_id=trigger_response.id)
            raise

        # Serialize the configuration back into the response
        trigger_response.set_action(config.dict(exclude_none=True))
        # Return the response to the user
        return trigger_response

    def update_trigger(
        self,
        trigger: TriggerResponse,
        trigger_update: TriggerUpdate,
    ) -> TriggerResponse:
        """Process a trigger update request and update the trigger in the database.

        Args:
            trigger: The trigger to update.
            trigger_update: The update to be applied to the trigger.

        Returns:
            The updated trigger.

        # noqa: DAR401
        """
        # Validate and instantiate the configuration from the original event
        # source
        config = self.validate_action_configuration(trigger.action)
        # Validate and instantiate the configuration from the update request
        # NOTE: if supplied, the configuration update is a full replacement
        # of the original configuration
        config_update = config
        if trigger_update.action is not None:
            config_update = self.validate_action_configuration(
                trigger_update.action
            )
        # Call the implementation specific method to validate the update request
        # before it is sent to the database
        self._validate_trigger_update(
            trigger=trigger,
            config=config,
            trigger_update=trigger_update,
            config_update=config_update,
        )
        # Serialize the configuration update back into the update request
        trigger_update.action = config_update.dict(exclude_none=True)

        # Update the trigger in the database
        trigger_response = self.zen_store.update_trigger(
            trigger_id=trigger.id,
            trigger_update=trigger_update,
        )
        try:
            # Instantiate the configuration from the response
            response_config = self.validate_action_configuration(
                trigger_response.action
            )
            # Call the implementation specific method to process the update
            # request before it is sent to the database
            self._process_trigger_update(
                trigger=trigger_response,
                config=response_config,
                previous_trigger=trigger,
                previous_config=config,
            )
            # Add any implementation specific related resources to the trigger
            # response
            self._populate_trigger_response_resources(
                trigger=trigger_response, config=response_config
            )
            # Deactivate the previous trigger and activate the updated trigger
            # in the event hub
            self.event_hub.deactivate_trigger(trigger=trigger)
            self.event_hub.activate_trigger(trigger=trigger_response)
        except Exception:
            # If the trigger update fails, roll back the trigger in
            # the database to the original state
            logger.exception(
                f"Failed to update trigger {trigger}. "
                f"Rolling back the trigger to the previous state."
            )
            self.zen_store.update_trigger(
                trigger_id=trigger.id,
                trigger_update=TriggerUpdate.from_response(trigger),
            )
            raise

        # Serialize the configuration back into the response
        trigger_response.set_action(response_config.dict(exclude_none=True))
        # Return the response to the user
        return trigger_response

    def delete_trigger(
        self,
        trigger: TriggerResponse,
        force: bool = False,
    ) -> None:
        """Process a trigger delete request and delete the trigger in the database.

        Args:
            trigger: The trigger to delete.
            force: Whether to force delete the trigger from the database
                even if the trigger handler fails to delete the event
                source.

        # noqa: DAR401
        """
        # Validate and instantiate the configuration from the original event
        # source
        config = self.validate_action_configuration(trigger.action)
        try:
            # Call the implementation specific method to process the deleted
            # trigger before it is deleted from the database
            self._process_trigger_delete(
                trigger=trigger,
                config=config,
                force=force,
            )
        except Exception:
            logger.exception(f"Failed to delete trigger {trigger}. ")
            if not force:
                raise

            logger.warning(f"Force deleting trigger {trigger}.")

        # Deactivate the trigger in the event hub
        self.event_hub.deactivate_trigger(trigger=trigger)

        # Delete the trigger from the database
        self.zen_store.delete_trigger(
            trigger_id=trigger.id,
        )

    def get_trigger(
        self, trigger: TriggerResponse, hydrate: bool = False
    ) -> TriggerResponse:
        """Process a trigger response before it is returned to the user.

        Args:
            trigger: The trigger fetched from the database.
            hydrate: Whether to hydrate the trigger.

        Returns:
            The trigger.
        """
        if hydrate:
            # Instantiate the configuration from the response
            config = self.validate_action_configuration(trigger.action)
            # Call the implementation specific method to process the response
            self._process_trigger_response(trigger=trigger, config=config)
            # Serialize the configuration back into the response
            trigger.set_action(config.dict(exclude_none=True))
            # Add any implementation specific related resources to the trigger
            # response
            self._populate_trigger_response_resources(
                trigger=trigger, config=config
            )

        # Return the response to the user
        return trigger

    def validate_action_configuration(
        self, action_config: Dict[str, Any]
    ) -> ActionConfig:
        """Validate and return the action configuration.

        Args:
            action_config: The actino configuration to validate.

        Returns:
            The validated action configuration.

        Raises:
            ValueError: if the configuration is invalid.
        """
        try:
            return self.config_class(**action_config)
        except ValueError as e:
            raise ValueError(f"Invalid configuration for action: {e}.") from e

    def extract_resources(
        self,
        action_config: ActionConfig,
    ) -> Dict[ResourceType, BaseResponse[Any, Any, Any]]:
        """Extract related resources for this action.

        Args:
            action_config: Action configuration from which to extract related
                resources.

        Returns:
            List of resources related to the action.
        """
        return {}

    def _validate_trigger_request(
        self, trigger: TriggerRequest, config: ActionConfig
    ) -> None:
        """Validate a trigger request before it is created in the database.

        Concrete action handlers should override this method to add
        implementation specific functionality pertaining to the validation of
        a new trigger. The implementation may also modify the trigger
        request and/or configuration in place to apply implementation specific
        changes before the request is stored in the database.

        If validation is required, the implementation should raise a
        ValueError if the configuration is invalid. If any exceptions are raised
        during the validation, the trigger will not be created in the
        database.

        The resulted action configuration is serialized back into the trigger
        request before it is stored in the database.

        The implementation should not use this method to provision any external
        resources, as the trigger may not be created in the database if
        the database level validation fails.

        Args:
            trigger: Trigger request.
            config: Action configuration instantiated from the request.
        """
        pass

    def _process_trigger_request(
        self, trigger: TriggerResponse, config: ActionConfig
    ) -> None:
        """Process a trigger request after it is created in the database.

        Concrete action handlers should override this method to add
        implementation specific functionality pertaining to the creation of
        a new trigger. The implementation may also modify the trigger
        response and/or configuration in place to apply implementation specific
        changes before the response is returned to the user.

        The resulted configuration is serialized back into the trigger
        response before it is returned to the user.

        The implementation should use this method to provision any external
        resources required for the trigger. If any of the provisioning
        fails, the implementation should raise an exception and the trigger
        will be deleted from the database.

        Args:
            trigger: Newly created trigger
            config: Action configuration instantiated from the response.
        """
        pass

    def _validate_trigger_update(
        self,
        trigger: TriggerResponse,
        config: ActionConfig,
        trigger_update: TriggerUpdate,
        config_update: ActionConfig,
    ) -> None:
        """Validate a trigger update before it is reflected in the database.

        Concrete action handlers should override this method to add
        implementation specific functionality pertaining to validation of an
        trigger update request. The implementation may also modify the
        trigger update and/or configuration update in place to apply
        implementation specific changes.

        If validation is required, the implementation should raise a
        ValueError if the configuration update is invalid. If any exceptions are
        raised during the validation, the trigger will not be updated in
        the database.

        The resulted configuration update is serialized back into the event
        source update before it is stored in the database.

        The implementation should not use this method to provision any external
        resources, as the trigger may not be updated in the database if
        the database level validation fails.

        Args:
            trigger: Original trigger before the update.
            config: Action configuration instantiated from the original
                trigger.
            trigger_update: Trigger update request.
            config_update: Action configuration instantiated from the
                updated trigger.
        """
        pass

    def _process_trigger_update(
        self,
        trigger: TriggerResponse,
        config: ActionConfig,
        previous_trigger: TriggerResponse,
        previous_config: ActionConfig,
    ) -> None:
        """Process a trigger after it is updated in the database.

        Concrete action handlers should override this method to add
        implementation specific functionality pertaining to updating an existing
        trigger. The implementation may also modify the trigger
        and/or configuration in place to apply implementation specific
        changes before the response is returned to the user.

        The resulted configuration is serialized back into the trigger
        response before it is returned to the user.

        The implementation should use this method to provision any external
        resources required for the trigger update. If any of the
        provisioning fails, the implementation should raise an exception and the
        trigger will be rolled back to the previous state in the database.

        Args:
            trigger: Trigger after the update.
            config: Action configuration instantiated from the updated
                trigger.
            previous_trigger: Original trigger before the update.
            previous_config: Action configuration instantiated from the
                original trigger.
        """
        pass

    def _process_trigger_delete(
        self,
        trigger: TriggerResponse,
        config: ActionConfig,
        force: Optional[bool] = False,
    ) -> None:
        """Process a trigger before it is deleted from the database.

        Concrete action handlers should override this method to add
        implementation specific functionality pertaining to the deletion of an
        trigger.

        The implementation should use this method to deprovision any external
        resources required for the trigger. If any of the deprovisioning
        fails, the implementation should raise an exception and the
        trigger will kept in the database (unless force is True, in which
        case the trigger will be deleted from the database regardless of
        any deprovisioning failures).

        Args:
            trigger: Trigger before the deletion.
            config: Action configuration before the deletion.
            force: Whether to force deprovision the trigger.
        """
        pass

    def _process_trigger_response(
        self, trigger: TriggerResponse, config: ActionConfig
    ) -> None:
        """Process a trigger response before it is returned to the user.

        Concrete action handlers should override this method to add
        implementation specific functionality pertaining to how the trigger
        response is returned to the user. The implementation may modify the
        the trigger response and/or configuration in place.

        The resulted configuration is serialized back into the trigger
        response before it is returned to the user.

        This method is applied to all trigger responses fetched from the
        database before they are returned to the user, with the exception of
        those returned from the `create_trigger`, `update_trigger`,
        and `delete_trigger` methods, which have their own specific
        processing methods.

        Args:
            trigger: Trigger response.
            config: Action configuration instantiated from the response.
        """
        pass

    def _populate_trigger_response_resources(
        self, trigger: TriggerResponse, config: ActionConfig
    ) -> None:
        """Populate related resources for the trigger response.

        Concrete action handlers should override this method to add
        implementation specific related resources to the trigger response.

        This method is applied to all trigger responses fetched from the
        database before they are returned to the user, including
        those returned from the `create_trigger`, `update_trigger`,
        and `delete_trigger` methods.

        Args:
            trigger: Trigger response.
            config: Action configuration instantiated from the response.
        """
        if trigger.resources is None:
            # We only populate the resources if the resources field is already
            # set by the database by means of hydration.
            return
        extract_resources = self.extract_resources(config)
        for resource_type, resource in extract_resources.items():
            setattr(trigger.resources, str(resource_type), resource)
