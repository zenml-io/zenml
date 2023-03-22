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
from types import TracebackType
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel

from zenml import __version__
from zenml.analytics.context import AnalyticsContext as AnalyticsContextV2
from zenml.constants import IS_DEBUG_ENV, SEGMENT_KEY_DEV, SEGMENT_KEY_PROD
from zenml.enums import StoreType
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
    BUILD_PIPELINE = "Pipeline built"

    # Repo
    INITIALIZE_REPO = "ZenML initialized"
    CONNECT_REPOSITORY = "Repository connected"
    UPDATE_REPOSITORY = "Repository updated"
    DELETE_REPOSITORY = "Repository deleted"

    # Template
    GENERATE_TEMPLATE = "Template generated"

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
    OPT_IN_OUT_EMAIL = "Response for Email prompt"

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

    # Workspaces
    CREATED_WORKSPACE = "Workspace created"
    CREATED_DEFAULT_WORKSPACE = "Default workspace created"
    UPDATED_WORKSPACE = "Workspace updated"
    DELETED_WORKSPACE = "Workspace deleted"
    SET_WORKSPACE = "Workspace set"

    # Role
    CREATED_ROLE = "Role created"
    CREATED_DEFAULT_ROLES = "Default roles created"
    UPDATED_ROLE = "Role updated"
    DELETED_ROLE = "Role deleted"

    # Flavor
    CREATED_FLAVOR = "Flavor created"
    UPDATED_FLAVOR = "Flavor updated"
    DELETED_FLAVOR = "Flavor deleted"

    # Secret
    CREATED_SECRET = "Secret created"
    UPDATED_SECRET = "Secret updated"
    DELETED_SECRET = "Secret deleted"

    # Test event
    EVENT_TEST = "Test event"

    # Stack recipes
    PULL_STACK_RECIPE = "Stack recipes pulled"
    RUN_STACK_RECIPE = "Stack recipe created"
    DESTROY_STACK_RECIPE = "Stack recipe destroyed"

    # ZenML server events
    ZENML_SERVER_STARTED = "ZenML server started"
    ZENML_SERVER_STOPPED = "ZenML server stopped"
    ZENML_SERVER_CONNECTED = "ZenML server connected"
    ZENML_SERVER_DEPLOYED = "ZenML server deployed"
    ZENML_SERVER_DESTROYED = "ZenML server destroyed"


class AnalyticsGroup(str, Enum):
    """Enum of event groups to track in segment."""

    ZENML_SERVER_GROUP = "ZenML server group"


def get_segment_key() -> str:
    """Get key for authorizing to Segment backend.

    Returns:
        Segment key as a string.
    """
    if IS_DEBUG_ENV:
        return SEGMENT_KEY_DEV
    else:
        return SEGMENT_KEY_PROD


class AnalyticsContext:
    """Context manager for analytics."""

    def __init__(self) -> None:
        """Context manager for analytics.

        Use this as a context manager to ensure that analytics are initialized
        properly, only tracked when configured to do so and that any errors
        are handled gracefully.
        """
        import analytics

        from zenml.config.global_config import GlobalConfiguration

        try:
            gc = GlobalConfiguration()

            self.analytics_opt_in = gc.analytics_opt_in
            self.user_id = str(gc.user_id)

            # That means user opted out of analytics
            if not gc.analytics_opt_in:
                return

            if analytics.write_key is None:
                analytics.write_key = get_segment_key()

            assert (
                analytics.write_key is not None
            ), "Analytics key not set but trying to make telemetry call."

            # Set this to 1 to avoid backoff loop
            analytics.max_retries = 1
        except Exception as e:
            self.analytics_opt_in = False
            logger.debug(f"Analytics initialization failed: {e}")

    def __enter__(self) -> "AnalyticsContext":
        """Enter context manager.

        Returns:
            Self.
        """
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
            True, we should never fail main thread.
        """
        if exc_val is not None:
            logger.debug(f"Sending telemetry data failed: {exc_val}")

        return True

    def identify(self, traits: Optional[Dict[str, Any]] = None) -> bool:
        """Identify the user.

        Args:
            traits: Traits of the user.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        import analytics

        logger.debug(
            f"Attempting to attach metadata to: User: {self.user_id}, "
            f"Metadata: {traits}"
        )

        if not self.analytics_opt_in:
            return False

        analytics.identify(self.user_id, traits)

        logger.debug(f"User data sent: User: {self.user_id},{traits}")

        return True

    def group(
        self,
        group: Union[str, AnalyticsGroup],
        group_id: str,
        traits: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Group the user.

        Args:
            group: Group to which the user belongs.
            group_id: Group ID.
            traits: Traits of the group.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        import analytics

        if isinstance(group, AnalyticsGroup):
            group = group.value

        if traits is None:
            traits = {}

        traits.update(
            {
                "group_id": group_id,
            }
        )

        logger.debug(
            f"Attempting to attach metadata to: User: {self.user_id}, "
            f"Group: {group}, Group ID: {group_id}, Metadata: {traits}"
        )

        if not self.analytics_opt_in:
            return False
        analytics.group(self.user_id, group_id, traits=traits)

        logger.debug(
            f"Group data sent: User: {self.user_id}, Group: {group}, Group ID: "
            f"{group_id}, Metadata: {traits}"
        )
        return True

    def track(
        self,
        event: Union[str, AnalyticsEvent],
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track an event.

        Args:
            event: Event to track.
            properties: Event properties.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        import analytics

        from zenml.config.global_config import GlobalConfiguration

        if isinstance(event, AnalyticsEvent):
            event = event.value

        if properties is None:
            properties = {}

        logger.debug(
            f"Attempting analytics: User: {self.user_id}, "
            f"Event: {event},"
            f"Metadata: {properties}"
        )

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
            }
        )

        gc = GlobalConfiguration()
        # avoid initializing the store in the analytics, to not create an
        # infinite loop
        if gc._zen_store is not None:
            zen_store = gc.zen_store
            user = zen_store.get_user()

            if "client_id" not in properties:
                properties["client_id"] = self.user_id
            if "user_id" not in properties:
                properties["user_id"] = str(user.id)

            if (
                zen_store.type == StoreType.REST
                and "server_id" not in properties
            ):
                server_info = zen_store.get_store_info()
                properties.update(
                    {
                        "user_id": str(user.id),
                        "server_id": str(server_info.id),
                        "server_deployment": str(server_info.deployment_type),
                        "database_type": str(server_info.database_type),
                        "secrets_store_type": str(
                            server_info.secrets_store_type
                        ),
                    }
                )

        for k, v in properties.items():
            if isinstance(v, UUID):
                properties[k] = str(v)

        analytics.track(self.user_id, event, properties)

        logger.debug(
            f"Analytics sent: User: {self.user_id}, Event: {event}, Metadata: "
            f"{properties}"
        )

        return True


def identify_user(
    user_metadata: Optional[Dict[str, Any]] = None,
    v1: Optional[bool] = True,
    v2: Optional[bool] = False,
) -> bool:
    """Attach metadata to user directly.

    Args:
        user_metadata: Dict of metadata to attach to the user.
        v1: Flag to determine whether analytics v1 is included.
        v2: Flag to determine whether analytics v2 is included.

    Returns:
        True if event is sent successfully, False is not.
    """
    success = True

    if user_metadata is None:
        return False

    if v1:
        with AnalyticsContext() as analytics:
            success_v1 = analytics.identify(traits=user_metadata)
            success = success and success_v1

    if v2:
        with AnalyticsContextV2() as analytics:
            success_v2 = analytics.identify(traits=user_metadata)
            success = success and success_v2

    return success


def identify_group(
    group: Union[str, AnalyticsGroup],
    group_id: UUID,
    group_metadata: Optional[Dict[str, Any]] = None,
    v1: Optional[bool] = True,
    v2: Optional[bool] = False,
) -> bool:
    """Attach metadata to a segment group.

    Args:
        group: Group to track.
        group_id: ID of the group.
        group_metadata: Metadata to attach to the group.
        v1: Flag to determine whether analytics v1 is included.
        v2: Flag to determine whether analytics v2 is included.

    Returns:
        True if event is sent successfully, False is not.
    """
    success = True

    if v1:
        with AnalyticsContext() as analytics:
            success_v1 = analytics.group(
                group=group, group_id=str(group_id), traits=group_metadata
            )
            success = success and success_v1

    if v2:
        with AnalyticsContextV2() as analytics:
            success_v2 = analytics.group(
                group_id=group_id, traits=group_metadata
            )
            success = success and success_v2

    return success


def track_event(
    event: AnalyticsEvent,
    metadata: Optional[Dict[str, Any]] = None,
    v1: Optional[bool] = True,
    v2: Optional[bool] = False,
) -> bool:
    """Track segment event if user opted-in.

    Args:
        event: Name of event to track in segment.
        metadata: Dict of metadata to track.
        v1: Flag to determine whether analytics v1 is included.
        v2: Flag to determine whether analytics v2 is included.

    Returns:
        True if event is sent successfully, False is not.
    """
    success = True

    if metadata is None:
        metadata = {}

    metadata.setdefault("event_success", True)

    if v1:
        with AnalyticsContext() as analytics:
            success_v1 = analytics.track(event=event, properties=metadata)
            success = success and success_v1

    if v2:
        with AnalyticsContextV2() as analytics:
            success_v2 = analytics.track(event=event, properties=metadata)
            success = success and success_v2

    return success


def parametrized(
    dec: Callable[..., Callable[..., Any]]
) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """A meta-decorator, that is, a decorator for decorators.

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
        event: AnalyticsEvent,
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

    ANALYTICS_FIELDS: ClassVar[List[str]] = []

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Get the analytics metadata for the model.

        Returns:
            Dict of analytics metadata.
        """
        metadata = {}
        for field_name in self.ANALYTICS_FIELDS:
            metadata[field_name] = getattr(self, field_name, None)
        return metadata


@parametrized
def track(
    func: Callable[..., Any],
    event: AnalyticsEvent,
    v1: Optional[bool] = True,
    v2: Optional[bool] = False,
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
        v1: Flag to determine whether analytics v1 is included.
        v2: Flag to determine whether analytics v2 is included.

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
        with event_handler(event=event, v1=v1, v2=v2) as handler:
            try:
                if len(args) and isinstance(args[0], AnalyticsTrackerMixin):
                    handler.tracker = args[0]

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


class event_handler(object):
    """Context handler to enable tracking the success status of an event."""

    def __init__(
        self,
        event: AnalyticsEvent,
        metadata: Optional[Dict[str, Any]] = None,
        v1: Optional[bool] = True,
        v2: Optional[bool] = False,
    ):
        """Initialization of the context manager.

        Args:
            event: The type of the analytics event
            metadata: The metadata of the event.
            v1: Flag to determine whether analytics v1 is included.
            v2: Flag to determine whether analytics v2 is included.
        """
        self.event: AnalyticsEvent = event
        self.metadata: Dict[str, Any] = metadata or {}
        self.tracker: Optional[AnalyticsTrackerMixin] = None
        self.v1: Optional[bool] = v1
        self.v2: Optional[bool] = v2

    def __enter__(self) -> "event_handler":
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

        if self.v1:
            if self.tracker:
                self.tracker.track_event(self.event, self.metadata)
            else:
                track_event(self.event, self.metadata, v1=True, v2=False)

        if self.v2:
            track_event(self.event, self.metadata, v1=False, v2=True)
