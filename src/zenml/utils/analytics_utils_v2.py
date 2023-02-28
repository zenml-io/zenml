#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
import os
from enum import Enum
from types import TracebackType
from typing import Callable, Any, Optional, Dict, Union, Type
from uuid import UUID

from analytics import Client

from zenml import __version__
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import SEGMENT_KEY_PROD_V2, ENV_ZENML_SERVER_FLAG
from zenml.environment import Environment, get_environment
from zenml.logger import get_logger
from zenml.models.server_models import ServerDatabaseType, ServerDeploymentType
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackedModelMixin,
    parametrized,
)
from zenml.zen_server.auth import get_auth_context

logger = get_logger(__name__)


@parametrized
def track_v2(
    func: Callable[..., Any],
    event: AnalyticsEvent,
) -> Callable[..., Any]:
    """Decorator to track event.

    If the decorated function takes in a `AnalyticsTrackedModelMixin` object as
    an argument or returns one, it will be called to track the event. The return
    value takes precedence over the argument when determining which object is
    called to track the event.

    If the decorated function is a method of a class that inherits from
    `AnalyticsTrackerMixin`, the parent object will be used to intermediate
    tracking analytics.

    Args:
        func: Function that is decorated.
        event: Event string to stamp with.

    Returns:
        Decorated function.
    """

    def inner_func(*args: Any, **kwargs: Any) -> Any:
        """Inner decorator function.

        Args:
            *args: Arguments to be passed to the function.
            **kwargs: Keyword arguments to be passed to the function.

        Returns:
            Result of the function.
        """
        with event_handler_v2(event) as handler:
            try:
                for obj in list(args) + list(kwargs.values()):
                    if isinstance(obj, AnalyticsTrackedModelMixin):
                        handler.metadata = obj.get_analytics_metadata()
                        break
            except Exception as e:
                logger.debug(f"Analytics tracking failure for {func}: {e}")

            result = func(*args, **kwargs)

            try:
                if isinstance(result, AnalyticsTrackedModelMixin):
                    handler.metadata = result.get_analytics_metadata()
            except Exception as e:
                logger.debug(f"Analytics tracking failure for {func}: {e}")

            return result

    inner_func.__doc__ = func.__doc__
    return inner_func


class event_handler_v2(object):
    """Context handler to enable tracking the success status of an event."""

    def __init__(
        self,
        event: AnalyticsEvent,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialization of the context manager.

        Args:
            event: The type of the analytics event
            metadata: The metadata of the event.
        """
        self.event: AnalyticsEvent = event
        self.metadata: Dict[str, Any] = metadata or {}

    def __enter__(self) -> "event_handler_v2":
        """Enter function of the event handler.

        Returns:
            the handler instance.
        """
        return self

    def __exit__(
        self,
        type_: Optional[Any],
        value: Optional[Any],
        traceback: Optional[Any],
    ) -> Any:
        """Exit function of the event handler.

        Checks whether there was a traceback and updates the metadata
        accordingly. Following the check, it calls the function to track the
        event.

        Args:
            type_: The class of the exception
            value: The instance of the exception
            traceback: The traceback of the exception

        """
        if traceback is not None:
            self.metadata.update({"event_success": False})
        else:
            self.metadata.update({"event_success": True})

        if type_ is not None:
            self.metadata.update({"event_error_type": type_.__name__})

        track_event_v2(self.event, self.metadata)


def track_event_v2(
    event: Union[str, AnalyticsEvent],
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Track segment event if user opted-in.

    Args:
        event: Name of event to track in segment.
        metadata: Dict of metadata to track.

    Returns:
        True if event is sent successfully, False is not.
    """
    if metadata is None:
        metadata = {}

    metadata.setdefault("event_success", True)

    with AnalyticsContextV2() as analytics_v2:
        return analytics_v2.track(event, metadata)

    return False


def identify_user_v2(user_metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Attach metadata to user directly.

    Args:
        user_metadata: Dict of metadata to attach to the user.

    Returns:
        True if event is sent successfully, False is not.
    """
    with AnalyticsContextV2() as analytics:
        if user_metadata is None:
            return False

        return analytics.identify(traits=user_metadata)

    return False


def identify_group_v2(
    group_id: str,
    group_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Attach metadata to a segment group.

    Args:
        group_id: ID of the group.
        group_metadata: Metadata to attach to the group.

    Returns:
        True if event is sent successfully, False is not.
    """
    with AnalyticsContextV2() as analytics:
        return analytics.group(group_id, traits=group_metadata)

    return False


def get_segment_key() -> str:
    """Get key for authorizing to Segment backend.

    Return:
        Segment key as string
    """
    return SEGMENT_KEY_PROD_V2


class AnalyticsContextV2:
    """Context manager for analytics."""

    def __init__(self) -> None:
        """Context manager for analytics.

        Use this as a context manager to ensure that analytics are initialized
        properly, only tracked when configured to do so and that any errors
        are handled gracefully.
        """
        self.analytics_opt_in: bool = False

        self.segment_client: Optional[Client] = None

        self.user_id: Optional[UUID] = None
        self.client_id: Optional[UUID] = None
        self.server_id: Optional[UUID] = None

        self.database_type: Optional[ServerDatabaseType] = None
        self.deployment_type: Optional[ServerDeploymentType] = None

    @property
    def is_server(self):
        """Flag to check whether the code is running on the server side."""
        return os.getenv(ENV_ZENML_SERVER_FLAG, False)

    def __enter__(self) -> "AnalyticsContextV2":
        """Enter analytics context manager.

        Returns:
            self.
        """
        # Fetch the analytics opt-in setting
        gc = GlobalConfiguration()
        self.analytics_opt_in = gc.analytics_opt_in

        if self.analytics_opt_in:
            # Create the segment client
            self.segment_client = Client(
                write_key=get_segment_key(),
                max_retries=1,
            )

            # Fetch the `user_id`
            if self.is_server:
                # If the code is running on the server side, use the auth context.
                auth_context = get_auth_context()
                if auth_context is not None:
                    self.user_id = auth_context.user.id
            else:
                # If the code is running on the client side, use the default user.
                default_user = gc.zen_store.get_user()
                self.user_id = default_user.id

            # Fetch the `client_id`
            if self.is_server:
                # If the code is running on the server side, there is no client id.
                self.client_id = None
            else:
                # If the code is running on the client side, attach the client id.
                self.client_id = gc.user_id

            # Fetch the store information including the `server_id`
            store_info = gc.zen_store.get_store_info()

            self.server_id = store_info.id
            self.deployment_type = store_info.deployment_type
            self.database_type = store_info.database_type

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Exit context manager.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.

        Returns:
            True if exception was handled, False otherwise.
        """
        if exc_val is not None:
            logger.debug("Sending telemetry data failed: {exc_val}")

        return True

    def identify(self, traits: Optional[Dict[str, Any]] = None) -> bool:
        """Identify the user through segment.

        Args:
            traits: Traits of the user.

        Returns:
            True if tracking information was sent, False otherwise.
        """

        if self.analytics_opt_in:
            self.segment_client.identify(self.user_id, traits)
            return True
        return False

    def group(
        self,
        group_id: str,
        traits: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Group the user.

        Args:
            group_id: Group ID.
            traits: Traits of the group.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        if self.analytics_opt_in:
            if traits is None:
                traits = {}

            traits.update({"group_id": group_id})

            self.segment_client.group(self.user_id, group_id, traits=traits)
            return True

        return False

    def track(
        self,
        event: AnalyticsEvent,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track an event.

        Args:
            event: Event to track.
            properties: Event properties.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        if not isinstance(event, AnalyticsEvent):
            raise ValueError(
                "When tracking events, please provide one of the supported "
                "event types."
            )

        event = event.value

        if properties is None:
            properties = {}

        if not self.analytics_opt_in and event not in {
            AnalyticsEvent.OPT_OUT_ANALYTICS,
            AnalyticsEvent.OPT_IN_ANALYTICS,
        }:
            return False

        # add basics
        properties.update(Environment.get_system_info())
        properties.update(
            {
                "environment": get_environment(),
                "python_version": Environment.python_version(),
                "version": __version__,
                "client_id": str(self.client_id),
                "user_id": str(self.user_id),
                "server_id": str(self.server_id),
                "deployment_type": str(self.deployment_type),
                "database_type": str(self.database_type),
            }
        )

        for k, v in properties.items():
            if isinstance(v, UUID):
                properties[k] = str(v)

        self.segment_client.track(self.user_id, event, properties)

        logger.debug(
            f"Analytics sent: User: {self.user_id}, Event: {event}, Metadata: "
            f"{properties}"
        )

        return True
