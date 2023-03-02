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
from types import TracebackType
from typing import Callable, Any, Optional, Dict, Union, Type, List
from uuid import UUID
import requests
from zenml import __version__
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_SERVER_FLAG, ANALYTICS_SERVER_URL

from zenml.environment import Environment, get_environment
from zenml.logger import get_logger
from zenml.models.server_models import ServerDatabaseType, ServerDeploymentType
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackedModelMixin,
    parametrized,
)
from zenml.zen_server.auth import get_auth_context
from pydantic import BaseModel

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


logger = get_logger(__name__)

TRACK_ENDPOINT = "/track"
GROUP_ENDPOINT = "/group"
IDENTIFY_ENDPOINT = "/identify"


class TrackRequest(BaseModel):
    """Base model for track requests.

    Attributes:
        user_id: the canonical ID of the user.
        event: the type of the event.
        properties: the metadata about the event.
    """

    user_id: UUID
    event: AnalyticsEvent
    properties: Dict[Any, Any]


class GroupRequest(BaseModel):
    """Base Model for group requests.

    Attributes:
        user_id: the canonical ID of the user.
        group_id: the ID of the group.
        traits: traits of the group.
    """

    user_id: UUID
    group_id: UUID
    traits: Dict[Any, Any]


class IdentifyRequest(BaseModel):
    """Base model for identify requests.

    Attributes:
        user_id: the canonical ID of the user.
        traits: traits of the identified user.
    """

    user_id: UUID
    traits: Dict[Any, Any]


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
        self, event: AnalyticsEvent, metadata: Optional[Dict[str, Any]] = None
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

    with AnalyticsClient() as analytics_v2:
        return analytics_v2.track(event, metadata)

    return False


class AnalyticsClient:
    """Client class for ZenML Analytics v2."""

    def __init__(self) -> None:
        """Initialization.

        Use this as a context manager to ensure that analytics are initialized
        properly, only tracked when configured to do so and that any errors
        are handled gracefully.
        """
        self.analytics_opt_in: bool = False

        self.user_id: Optional[UUID] = None
        self.client_id: Optional[UUID] = None
        self.server_id: Optional[UUID] = None

        self.database_type: Optional[ServerDatabaseType] = None
        self.deployment_type: Optional[ServerDeploymentType] = None

    @property
    def in_server(self):
        """Flag to check whether the code is running on the server side."""
        return os.getenv(ENV_ZENML_SERVER_FLAG, False)

    def __enter__(self) -> "AnalyticsClient":
        """Enter analytics context manager.

        Returns:
            self.
        """
        # Fetch the analytics opt-in setting
        gc = GlobalConfiguration()
        self.analytics_opt_in = gc.analytics_opt_in

        if self.analytics_opt_in:
            try:
                # Fetch the `user_id`
                if self.in_server:
                    # If the code is running on the server side, use the auth context.
                    auth_context = get_auth_context()
                    if auth_context is not None:
                        self.user_id = auth_context.user.id
                else:
                    # If the code is running on the client side, use the default user.
                    default_user = gc.zen_store.get_user()
                    self.user_id = default_user.id

                # Fetch the `client_id`
                if self.in_server:
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
            except Exception as e:
                self.analytics_opt_in = False
                logger.debug(f"Analytics initialization failed: {e}")
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
            logger.debug(f"Sending telemetry data failed: {exc_val}")

        return True

    def _post(self, endpoint, payload) -> Json:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        return self._handle_response(
            requests.post(
                url=ANALYTICS_SERVER_URL + endpoint,
                headers=headers,
                json=payload.json(),
            )
        )

    def identify(self, traits: Optional[Dict[str, Any]] = None) -> bool:
        """Identify the user through segment.

        Args:
            traits: Traits of the user.

        Returns:
            True if tracking information was sent, False otherwise.
        """

        if self.analytics_opt_in:
            payload = TrackRequest(
                user_id=self.user_id,
                traits=traits,
            )
            self._post(endpoint=IDENTIFY_ENDPOINT, payload=payload)

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

            payload = GroupRequest(
                user_id=self.user_id,
                group_id=group_id,
                traits=traits,
            )

            self._post(endpoint=GROUP_ENDPOINT, payload=payload)
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

        if properties is None:
            properties = {}

        if not self.analytics_opt_in and event.value not in {
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

        payload = TrackRequest(
            user_id=self.user_id,
            event=event,
            properties=properties,
        )

        self._post(endpoint=TRACK_ENDPOINT, payload=payload)

        logger.debug(
            f"Analytics sent: User: {self.user_id}, Event: {event}, Metadata: "
            f"{properties}"
        )

        return True

    @staticmethod
    def _handle_response(response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception.

        Args:
            response: The response to handle.

        Returns:
            The parsed response.
        """
        if 200 <= response.status_code < 300:
            try:
                payload: Json = response.json()
                return payload
            except requests.exceptions.JSONDecodeError:
                logger.debug(
                    "Bad response from API. Expected json, got\n"
                    f"{response.text}"
                )
        elif response.status_code == 422:
            response_details = response.json().get("detail", (response.text,))
            if isinstance(response_details[0], str):
                response_msg = ": ".join(response_details)
            else:
                # This is an "Unprocessable Entity" error, which has a special
                # structure in the response.
                response_msg = response.text
            raise logger.debug(response_msg)
        else:
            raise logger.debug(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )
