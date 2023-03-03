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
from typing import Callable, Any, Optional, Dict, Union, List

from zenml.logger import get_logger
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackedModelMixin,
    parametrized,
)
from zenml.analytics.context import AnalyticsContext
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

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

    with AnalyticsContext() as analytics_v2:
        return analytics_v2.track(event, metadata)

    return False
