#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the ZenML Service class."""

import json
import time
from abc import abstractmethod
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    Optional,
    Tuple,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import ConfigDict

from zenml.console import console
from zenml.enums import ServiceState
from zenml.logger import get_logger
from zenml.models.v2.misc.service import ServiceType
from zenml.services.service_endpoint import BaseServiceEndpoint
from zenml.services.service_monitor import HTTPEndpointHealthMonitor
from zenml.services.service_status import ServiceStatus
from zenml.utils import source_utils
from zenml.utils.typed_model import BaseTypedModel

logger = get_logger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

if TYPE_CHECKING:
    from zenml.models.v2.core.service import ServiceResponse

ZENM_ENDPOINT_PREFIX = "zenml-"


def update_service_status(
    pre_status: Optional[ServiceState] = None,
    post_status: Optional[ServiceState] = None,
    error_status: ServiceState = ServiceState.ERROR,
) -> Callable[[T], T]:
    """A decorator to update the service status before and after a method call.

    This decorator is used to wrap service methods and update the service status
    before and after the method call. If the method raises an exception, the
    service status is updated to reflect the error state.

    Args:
        pre_status: the status to update before the method call.
        post_status: the status to update after the method call.
        error_status: the status to update if the method raises an exception.

    Returns:
        Callable[..., Any]: The wrapped method with exception handling.
    """

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(self: "BaseService", *args: Any, **kwargs: Any) -> Any:
            if pre_status:
                self.status.update_state(pre_status, "")
            try:
                logger.debug(f"Calling {func.__name__} method...")
                result = func(self, *args, **kwargs)
                logger.debug(f"{func.__name__} method executed successfully.")
                if post_status:
                    self.status.update_state(post_status, "")
                return result
            except Exception as e:
                logger.error(
                    f"Error occurred in {func.__name__} method: {str(e)}"
                )
                self.status.update_state(error_status, str(e))
                raise

        return wrapper  # type: ignore

    return decorator


class ServiceConfig(BaseTypedModel):
    """Generic service configuration.

    Concrete service classes should extend this class and add additional
    attributes that they want to see reflected and used in the service
    configuration.

    Attributes:
        name: name for the service instance
        description: description of the service
        pipeline_name: name of the pipeline that spun up the service
        pipeline_step_name: name of the pipeline step that spun up the service
        run_name: name of the pipeline run that spun up the service.
    """

    name: str = ""
    description: str = ""
    pipeline_name: str = ""
    pipeline_step_name: str = ""
    model_name: str = ""
    model_version: str = ""
    service_name: str = ""

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    def __init__(self, **data: Any):
        """Initialize the service configuration.

        Args:
            **data: keyword arguments.

        Raises:
            ValueError: if neither 'name' nor 'model_name' is set.
        """
        super().__init__(**data)
        if self.name or self.model_name:
            self.service_name = data.get(
                "service_name",
                f"{ZENM_ENDPOINT_PREFIX}{self.name or self.model_name}",
            )
        else:
            raise ValueError("Either 'name' or 'model_name' must be set.")

    def get_service_labels(self) -> Dict[str, str]:
        """Get the service labels.

        Returns:
            a dictionary of service labels.
        """
        labels = {}
        for k, v in self.model_dump().items():
            label = f"zenml_{k}".upper()
            labels[label] = str(v)
        return labels


class BaseService(BaseTypedModel):
    """Base service class.

    This class implements generic functionality concerning the life-cycle
    management and tracking of an external service (e.g. process, container,
    Kubernetes deployment etc.).

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the service class. Every concrete service class must define this.
        admin_state: the administrative state of the service.
        uuid: unique UUID identifier for the service instance.
        config: service configuration
        status: service status
        endpoint: optional service endpoint
    """

    SERVICE_TYPE: ClassVar[ServiceType]

    uuid: UUID
    admin_state: ServiceState = ServiceState.INACTIVE
    config: ServiceConfig
    status: ServiceStatus
    # TODO [ENG-703]: allow multiple endpoints per service
    endpoint: Optional[BaseServiceEndpoint] = None

    def __init__(
        self,
        **attrs: Any,
    ) -> None:
        """Initialize the service instance.

        Args:
            **attrs: keyword arguments.
        """
        super().__init__(**attrs)
        self.config.name = self.config.name or self.__class__.__name__

    @classmethod
    def from_model(cls, model: "ServiceResponse") -> "BaseService":
        """Loads a service from a model.

        Args:
            model: The ServiceResponse to load from.

        Returns:
            The loaded service object.

        Raises:
            ValueError: if the service source is not found in the model.
        """
        if not model.service_source:
            raise ValueError("Service source not found in the model.")
        class_: Type[BaseService] = source_utils.load_and_validate_class(
            source=model.service_source, expected_class=BaseService
        )
        return class_(
            uuid=model.id,
            admin_state=model.admin_state,
            config=model.config,
            status=model.status,
            service_type=model.service_type.model_dump(),
            endpoint=model.endpoint,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "BaseTypedModel":
        """Loads a service from a JSON string.

        Args:
            json_str: the JSON string to load from.

        Returns:
            The loaded service object.
        """
        service_dict = json.loads(json_str)
        class_: Type[BaseService] = source_utils.load_and_validate_class(
            source=service_dict["type"], expected_class=BaseService
        )
        return class_.from_dict(service_dict)

    @abstractmethod
    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the external service.

        This method should be overridden by subclasses that implement
        concrete service tracking functionality.

        Returns:
            The operational state of the external service and a message
            providing additional information about that state (e.g. a
            description of the error if one is encountered while checking the
            service status).
        """

    @abstractmethod
    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        This method should be overridden by subclasses that implement
        concrete service tracking functionality.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """

    def update_status(self) -> None:
        """Update the status of the service.

        Check the current operational state of the external service
        and update the local operational status information to reflect it.

        This method should be overridden by subclasses that implement
        concrete service status tracking functionality.
        """
        logger.debug(
            "Running status check for service '%s' ...",
            self,
        )
        try:
            state, err = self.check_status()
            logger.debug(
                "Status check results for service '%s': %s [%s]",
                self,
                state.name,
                err,
            )
            self.status.update_state(state, err)

            # don't bother checking the endpoint state if the service is not active
            if self.status.state == ServiceState.INACTIVE:
                return

            if self.endpoint:
                self.endpoint.update_status()
        except Exception as e:
            logger.error(
                f"Failed to update status for service '{self}': {e}",
                exc_info=True,
            )
            self.status.update_state(ServiceState.ERROR, str(e))

    def get_service_status_message(self) -> str:
        """Get a service status message.

        Returns:
            A message providing information about the current operational
            state of the service.
        """
        return (
            f"  Administrative state: `{self.admin_state.value}`\n"
            f"  Operational state: `{self.status.state.value}`\n"
            f"  Last status message: '{self.status.last_error}'\n"
        )

    def poll_service_status(self, timeout: int = 0) -> bool:
        """Polls the external service status.

        It does this until the service operational state matches the
        administrative state, the service enters a failed state, or the timeout
        is reached.

        Args:
            timeout: maximum time to wait for the service operational state
                to match the administrative state, in seconds

        Returns:
            True if the service operational state matches the administrative
            state, False otherwise.
        """
        time_remaining = timeout
        while True:
            if self.admin_state == ServiceState.ACTIVE and self.is_running:
                return True
            if self.admin_state == ServiceState.INACTIVE and self.is_stopped:
                return True
            if self.is_failed:
                return False
            if time_remaining <= 0:
                break
            time.sleep(1)
            time_remaining -= 1

        if timeout > 0:
            logger.error(
                f"Timed out waiting for service {self} to become "
                f"{self.admin_state.value}:\n"
                + self.get_service_status_message()
            )

        return False

    @property
    def is_running(self) -> bool:
        """Check if the service is currently running.

        This method will actively poll the external service to get its status
        and will return the result.

        Returns:
            True if the service is running and active (i.e. the endpoints are
            responsive, if any are configured), otherwise False.
        """
        self.update_status()
        return self.status.state == ServiceState.ACTIVE and (
            not self.endpoint or self.endpoint.is_active()
        )

    @property
    def is_stopped(self) -> bool:
        """Check if the service is currently stopped.

        This method will actively poll the external service to get its status
        and will return the result.

        Returns:
            True if the service is stopped, otherwise False.
        """
        self.update_status()
        return self.status.state == ServiceState.INACTIVE

    @property
    def is_failed(self) -> bool:
        """Check if the service is currently failed.

        This method will actively poll the external service to get its status
        and will return the result.

        Returns:
            True if the service is in a failure state, otherwise False.
        """
        self.update_status()
        return self.status.state == ServiceState.ERROR

    def provision(self) -> None:
        """Provisions resources to run the service.

        Raises:
            NotImplementedError: if the service does not implement provisioning functionality
        """
        raise NotImplementedError(
            f"Provisioning resources not implemented for {self}."
        )

    def deprovision(self, force: bool = False) -> None:
        """Deprovisions all resources used by the service.

        Args:
            force: if True, the service will be deprovisioned even if it is
                in a failed state.

        Raises:
            NotImplementedError: if the service does not implement
                deprovisioning functionality.
        """
        raise NotImplementedError(
            f"Deprovisioning resources not implemented for {self}."
        )

    def update(self, config: ServiceConfig) -> None:
        """Update the service configuration.

        Args:
            config: the new service configuration.
        """
        self.config = config

    @update_service_status(
        pre_status=ServiceState.PENDING_STARTUP,
        post_status=ServiceState.ACTIVE,
    )
    def start(self, timeout: int = 0) -> None:
        """Start the service and optionally wait for it to become active.

        Args:
            timeout: amount of time to wait for the service to become active.
                If set to 0, the method will return immediately after checking
                the service status.
        """
        with console.status(f"Starting service '{self}'.\n"):
            self.admin_state = ServiceState.ACTIVE
            self.provision()
            if timeout > 0 and not self.poll_service_status(timeout):
                logger.error(
                    f"Failed to start service {self}\n"
                    + self.get_service_status_message()
                )

    @update_service_status(
        pre_status=ServiceState.PENDING_SHUTDOWN,
        post_status=ServiceState.INACTIVE,
    )
    def stop(self, timeout: int = 0, force: bool = False) -> None:
        """Stop the service and optionally wait for it to shutdown.

        Args:
            timeout: amount of time to wait for the service to shutdown.
                If set to 0, the method will return immediately after checking
                the service status.
            force: if True, the service will be stopped even if it is not
                currently running.
        """
        with console.status(f"Stopping service '{self}'.\n"):
            self.admin_state = ServiceState.INACTIVE
            self.deprovision(force)
            if timeout > 0:
                self.poll_service_status(timeout)
                if not self.is_stopped:
                    logger.error(
                        f"Failed to stop service {self}. Last state: "
                        f"'{self.status.state.value}'. Last error: "
                        f"'{self.status.last_error}'"
                    )

    def get_prediction_url(self) -> Optional[str]:
        """Gets the prediction URL for the endpoint.

        Returns:
            the prediction URL for the endpoint
        """
        prediction_url = None
        if isinstance(self, BaseDeploymentService) and self.prediction_url:
            prediction_url = self.prediction_url
        elif self.endpoint:
            prediction_url = (
                self.endpoint.status.uri if self.endpoint.status else None
            )
        return prediction_url

    def get_healthcheck_url(self) -> Optional[str]:
        """Gets the healthcheck URL for the endpoint.

        Returns:
            the healthcheck URL for the endpoint
        """
        return (
            self.endpoint.monitor.get_healthcheck_uri(self.endpoint)
            if (self.endpoint and self.endpoint.monitor)
            and isinstance(self.endpoint.monitor, HTTPEndpointHealthMonitor)
            else None
        )

    def __repr__(self) -> str:
        """String representation of the service.

        Returns:
            A string representation of the service.
        """
        return f"{self.__class__.__qualname__}[{self.uuid}] (type: {self.SERVICE_TYPE.type}, flavor: {self.SERVICE_TYPE.flavor})"

    def __str__(self) -> str:
        """String representation of the service.

        Returns:
            A string representation of the service.
        """
        return self.__repr__()

    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
    )


class BaseDeploymentService(BaseService):
    """Base class for deployment services."""

    @property
    def prediction_url(self) -> Optional[str]:
        """Gets the prediction URL for the endpoint.

        Returns:
            the prediction URL for the endpoint
        """
        return None

    @property
    def healthcheck_url(self) -> Optional[str]:
        """Gets the healthcheck URL for the endpoint.

        Returns:
            the healthcheck URL for the endpoint
        """
        return None
