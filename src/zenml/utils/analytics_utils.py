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
"""Analytics code for ZenML."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel

from zenml import __version__
from zenml.constants import IS_DEBUG_ENV, SEGMENT_KEY_DEV, SEGMENT_KEY_PROD
from zenml.environment import Environment, get_environment
from zenml.logger import get_logger

logger = get_logger(__name__)


class AnalyticsEvent(str, Enum):
    """Enum of events to track in segment."""

    # Pipelines
    RUN_PIPELINE = "Pipeline run"
    GET_PIPELINES = "Pipelines fetched"
    GET_PIPELINE = "Pipeline fetched"
    CREATE_PIPELINE = "Pipeline created"
    UPDATE_PIPELINE = "Pipeline updated"
    DELETE_PIPELINE = "Pipeline deleted"

    # Repo
    INITIALIZE_REPO = "ZenML initialized"
    CONNECT_REPOSITORY = "Repository connected"
    UPDATE_REPOSITORY = "Repository updated"
    DELETE_REPOSITORY = "Repository deleted"

    # Zen store
    INITIALIZED_STORE = "Store initialized"

    # Components
    REGISTERED_STACK_COMPONENT = "Stack component registered"
    UPDATED_STACK_COMPONENT = "Stack component updated"
    COPIED_STACK_COMPONENT = "Stack component copied"
    DELETED_STACK_COMPONENT = "Stack component copied"

    # Stack
    REGISTERED_STACK = "Stack registered"
    REGISTERED_DEFAULT_STACK = "Default stack registered"
    SET_STACK = "Stack set"
    UPDATED_STACK = "Stack updated"
    COPIED_STACK = "Stack copied"
    IMPORT_STACK = "Stack imported"
    EXPORT_STACK = "Stack exported"
    DELETED_STACK = "Stack deleted"

    # Model Deployment
    MODEL_DEPLOYED = "Model deployed"

    # Analytics opt in and out
    OPT_IN_ANALYTICS = "Analytics opt-in"
    OPT_OUT_ANALYTICS = "Analytics opt-out"

    # Examples
    RUN_ZENML_GO = "ZenML go"
    RUN_EXAMPLE = "Example run"
    PULL_EXAMPLE = "Example pull"

    # Integrations
    INSTALL_INTEGRATION = "Integration installed"

    # Users
    CREATED_USER = "User created"
    CREATED_DEFAULT_USER = "Default user created"
    UPDATED_USER = "User updated"
    DELETED_USER = "User deleted"

    # Teams
    CREATED_TEAM = "Team created"
    UPDATED_TEAM = "Team updated"
    DELETED_TEAM = "Team deleted"

    # Projects
    CREATED_PROJECT = "Project created"
    CREATED_DEFAULT_PROJECT = "Default project created"
    UPDATED_PROJECT = "Project updated"
    DELETED_PROJECT = "Project deleted"
    SET_PROJECT = "Project set"

    # Role
    CREATED_ROLE = "Role created"
    UPDATED_ROLE = "Role updated"
    DELETED_ROLE = "Role deleted"

    # Flavor
    CREATED_FLAVOR = "Flavor created"

    # Test event
    EVENT_TEST = "Test event"

    # Login events
    LOGIN = "Login"
    LOGOUT = "Logout"

    # Stack recipes
    PULL_STACK_RECIPE = "Stack recipes pulled"
    RUN_STACK_RECIPE = "Stack recipe created"
    DESTROY_STACK_RECIPE = "Stack recipe destroyed"


def get_segment_key() -> str:
    """Get key for authorizing to Segment backend.

    Returns:
        Segment key as a string.
    """
    if IS_DEBUG_ENV:
        return SEGMENT_KEY_DEV
    else:
        return SEGMENT_KEY_PROD


def identify_user(user_metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Attach metadata to user directly.

    Args:
        user_metadata: Dict of metadata to attach to the user.

    Returns:
        True if event is sent successfully, False is not.
    """
    # TODO [ENG-857]: The identify_user function shares a lot of setup with
    #  track_event() - this duplicated code could be given its own function
    try:
        from zenml.config.global_config import GlobalConfiguration

        gc = GlobalConfiguration()

        # That means user opted out of analytics
        if not gc.analytics_opt_in:
            return False

        import analytics

        if analytics.write_key is None:
            analytics.write_key = get_segment_key()

        assert (
            analytics.write_key is not None
        ), "Analytics key not set but trying to make telemetry call."

        # Set this to 1 to avoid backoff loop
        analytics.max_retries = 1

        logger.debug(
            f"Attempting to attach metadata to: User: {gc.user_id}, "
            f"Metadata: {user_metadata}"
        )

        if user_metadata is None:
            return False

        analytics.identify(str(gc.user_id), traits=user_metadata)
        logger.debug(f"User data sent: User: {gc.user_id},{user_metadata}")
        return True
    except Exception as e:
        # We should never fail main thread
        logger.error(f"User data update failed due to: {e}")
        return False


def track_event(
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
    try:
        import analytics

        from zenml.config.global_config import GlobalConfiguration

        if analytics.write_key is None:
            analytics.write_key = get_segment_key()

        assert (
            analytics.write_key is not None
        ), "Analytics key not set but trying to make telemetry call."

        # Set this to 1 to avoid backoff loop
        analytics.max_retries = 1

        gc = GlobalConfiguration()
        if isinstance(event, AnalyticsEvent):
            event = event.value

        logger.debug(
            f"Attempting analytics: User: {gc.user_id}, "
            f"Event: {event},"
            f"Metadata: {metadata}"
        )

        if not gc.analytics_opt_in and event not in {
            AnalyticsEvent.OPT_OUT_ANALYTICS,
            AnalyticsEvent.OPT_IN_ANALYTICS,
        }:
            return False

        if metadata is None:
            metadata = {}

        # add basics
        metadata.update(Environment.get_system_info())
        metadata.update(
            {
                "environment": get_environment(),
                "python_version": Environment.python_version(),
                "version": __version__,
            }
        )

        analytics.track(str(gc.user_id), event, metadata)
        logger.debug(
            f"Analytics sent: User: {gc.user_id}, Event: {event}, Metadata: "
            f"{metadata}"
        )
        return True
    except Exception as e:
        # We should never fail main thread
        logger.debug(f"Analytics failed due to: {e}")
        return False


def parametrized(
    dec: Callable[..., Callable[..., Any]]
) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """This is a meta-decorator, that is, a decorator for decorators.

    As a decorator is a function, it actually works as a regular decorator
    with arguments.

    Args:
        dec: Decorator to be applied to the function.

    Returns:
        Decorator that applies the given decorator to the function.
    """

    def layer(
        *args: Any, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Internal layer.

        Args:
            *args: Arguments to be passed to the decorator.
            **kwargs: Keyword arguments to be passed to the decorator.

        Returns:
            Decorator that applies the given decorator to the function.
        """

        def repl(f: Callable[..., Any]) -> Callable[..., Any]:
            """Internal REPL.

            Args:
                f: Function to be decorated.

            Returns:
                Decorated function.
            """
            return dec(f, *args, **kwargs)

        return repl

    return layer


class AnalyticsTrackerMixin(ABC):
    """Abstract base class for analytics trackers.

    Use this as a mixin for classes that have methods decorated with
    `@track` to add global control over how analytics are tracked. The decorator
    will detect that the class has this mixin and will call the class
    `track_event` method.
    """

    @abstractmethod
    def track_event(
        self,
        event: Union[str, AnalyticsEvent],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Track an event.

        Args:
            event: Event to track.
            metadata: Metadata to track.
        """


class AnalyticsTrackedModelMixin(BaseModel):
    """Mixin for models that are tracked through analytics events.

    Classes that have information tracked in analytics events can inherit
    from this mixin and implement the abstract methods. The `@track` decorator
    will detect function arguments and return values that inherit from this
    class and will include the `ANALYTICS_FIELDS` attributes as
    tracking metadata.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]]

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Get the analytics metadata for the model.

        Returns:
            Dict of analytics metadata.
        """
        metadata = {}
        for field_name in self.ANALYTICS_FIELDS:
            metadata[field_name] = getattr(self, field_name, None)
        return metadata

    def track_event(
        self,
        event: Union[str, AnalyticsEvent],
        tracker: Optional[AnalyticsTrackerMixin] = None,
    ) -> None:
        """Track an event for the model.

        Args:
            event: Event to track.
            tracker: Optional tracker to use for analytics.
        """
        metadata = self.get_analytics_metadata()
        if tracker:
            tracker.track_event(event, metadata)
        else:
            track_event(event, metadata)


@parametrized
def track(
    func: Callable[..., Any],
    event: Optional[Union[str, AnalyticsEvent]] = None,
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
    event_name = event or func.__name__  # default to name of function
    metadata: Dict[str, Any] = {}

    def inner_func(*args: Any, **kwargs: Any) -> Any:
        """Inner decorator function.

        Args:
            *args: Arguments to be passed to the function.
            **kwargs: Keyword arguments to be passed to the function.

        Returns:
            Result of the function.
        """
        result = func(*args, **kwargs)
        try:
            tracker: Optional[AnalyticsTrackerMixin] = None
            if len(args) and isinstance(args[0], AnalyticsTrackerMixin):
                tracker = args[0]
            for obj in [result] + list(args) + list(kwargs.values()):
                if isinstance(obj, AnalyticsTrackedModelMixin):
                    obj.track_event(event_name, tracker=tracker)
                    break
            else:
                if tracker:
                    tracker.track_event(event_name, metadata)
                else:
                    track_event(event_name, metadata)

        except Exception as e:
            logger.debug(f"Analytics tracking failure for {func}: {e}")

        return result

    return inner_func
