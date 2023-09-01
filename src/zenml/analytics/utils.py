#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Utility functions and classes for ZenML analytics."""
import json
import os
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from uuid import UUID

from zenml.analytics import identify, track
from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.models import AnalyticsTrackedModelMixin
from zenml.constants import ENV_ZENML_ANALYTICS_OPT_IN
from zenml.logger import get_logger

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


class AnalyticsEncoder(json.JSONEncoder):
    """Helper encoder class for JSON serialization."""

    def default(self, obj: Any) -> Any:
        """The default method to handle UUID and 'AnalyticsEvent' objects.

        Args:
            obj: The object to encode.

        Returns:
            The encoded object.
        """
        from zenml.analytics.enums import AnalyticsEvent

        # If the object is UUID, we simply return the value of UUID
        if isinstance(obj, UUID):
            return str(obj)

        # If the object is an AnalyticsEvent, return its value
        elif isinstance(obj, AnalyticsEvent):
            return str(obj.value)

        return json.JSONEncoder.default(self, obj)


class AnalyticsAPIError(Exception):
    """Custom exception class for API-related errors."""

    def __init__(self, status: int, message: str) -> None:
        """Initialization.

        Args:
            status: The status code of the response.
            message: The text of the response.
        """
        self.message = message
        self.status = status

    def __str__(self) -> str:
        """Method to represent the instance as a string.

        Returns:
            A representation of the message and the status code.
        """
        msg = "[ZenML Analytics] {1}: {0}"
        return msg.format(self.message, self.status)


def email_opt_int(opted_in: bool, email: Optional[str], source: str) -> None:
    """Track the event of the users response to the email prompt, identify them.

    Args:
        opted_in: Did the user decide to opt-in
        email: The email the user optionally provided
        source: Location when the user replied ["zenml go", "zenml server"]
    """
    # If the user opted in, associate email with the anonymous distinct ID
    if opted_in and email is not None and email != "":
        identify(metadata={"email": email, "source": source})

    # Track that the user answered the prompt
    track(
        AnalyticsEvent.OPT_IN_OUT_EMAIL,
        {"opted_in": opted_in, "source": source},
    )


class analytics_disabler:
    """Context manager which disables ZenML analytics."""

    def __init__(self) -> None:
        """Initialization of the context manager."""
        self.original_value = os.environ.get(ENV_ZENML_ANALYTICS_OPT_IN)

    def __enter__(self) -> None:
        """Disable the analytics."""
        os.environ[ENV_ZENML_ANALYTICS_OPT_IN] = str(False)

    def __exit__(
        self,
        exc_type: Optional[Any],
        exc_value: Optional[Any],
        traceback: Optional[Any],
    ) -> None:
        """Set it back to the original state.

        Args:
            exc_type: The class of the exception
            exc_value: The instance of the exception
            traceback: The traceback of the exception
        """
        if self.original_value is not None:
            os.environ[ENV_ZENML_ANALYTICS_OPT_IN] = self.original_value
        else:
            del os.environ[ENV_ZENML_ANALYTICS_OPT_IN]


def track_decorator(event: AnalyticsEvent) -> Callable[[F], F]:
    """Decorator to track event.

    If the decorated function takes in a `AnalyticsTrackedModelMixin` object as
    an argument or returns one, it will be called to track the event. The return
    value takes precedence over the argument when determining which object is
    called to track the event.

    If the decorated function is a method of a class that inherits from
    `AnalyticsTrackerMixin`, the parent object will be used to intermediate
    tracking analytics.

    Args:
        event: Event string to stamp with.

    Returns:
        A decorator that applies the analytics tracking to a function.
    """

    def inner_decorator(func: F) -> F:
        """Inner decorator function.

        Args:
            func: Function to decorate.

        Returns:
            Decorated function.
        """

        @wraps(func)
        def inner_func(*args: Any, **kwargs: Any) -> Any:
            """Inner function.

            Args:
                *args: Arguments to be passed to the function.
                **kwargs: Keyword arguments to be passed to the function.

            Returns:
                Result of the function.
            """
            with track_handler(event=event) as handler:
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

        return cast(F, inner_func)

    return inner_decorator


class track_handler(object):
    """Context handler to enable tracking the success status of an event."""

    def __init__(
        self,
        event: AnalyticsEvent,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialization of the context manager.

        Args:
            event: The type of the analytics event
            metadata: The metadata of the event.
        """
        self.event: AnalyticsEvent = event
        self.metadata: Dict[str, Any] = metadata or {}

    def __enter__(self) -> "track_handler":
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

        track(self.event, self.metadata)
