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

import time
from abc import abstractmethod
from typing import Any, ClassVar, Dict, Generator, Optional, Tuple, Type, cast
from uuid import UUID, uuid4

from pydantic import Field

from zenml.console import console
from zenml.logger import get_logger
from zenml.services.service_endpoint import BaseServiceEndpoint
from zenml.services.service_registry import ServiceRegistry
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.services.service_type import ServiceType
from zenml.utils.typed_model import BaseTypedModel, BaseTypedModelMeta

logger = get_logger(__name__)


class ServiceConfig(BaseTypedModel):
    """Generic service configuration.

    Concrete service classes should extend this class and add additional
    attributes that they want to see reflected and used in the service
    configuration.

    Attributes:
        name: name for the service instance
        description: description of the service
        pipeline_name: name of the pipeline that spun up the service
        pipeline_run_id: ID of the pipeline run that spun up the service
        pipeline_step_name: name of the pipeline step that spun up the service
    """

    name: str = ""
    description: str = ""
    pipeline_name: str = ""
    pipeline_run_id: str = ""
    pipeline_step_name: str = ""


class BaseServiceMeta(BaseTypedModelMeta):
    """Metaclass responsible for registering different BaseService
    subclasses.

    This metaclass has two main responsibilities:
    1. register all BaseService types in the service registry. This is relevant
    when services are deserialized and instantiated from their JSON or dict
    representation, because their type needs to be known beforehand.
    2. ensuring BaseService instance uniqueness by enforcing that no two
    service instances have the same UUID value. Implementing this at the
    constructor level guarantees that deserializing a service instance from
    a JSON representation multiple times always returns the same service object.
    """

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseServiceMeta":
        """Creates a BaseService class and registers it in
        the `ServiceRegistry`."""
        service_type = dct.get("SERVICE_TYPE", None)

        # register only classes of concrete service implementations
        if service_type:
            # add the service type class attribute to the class as a regular
            # immutable attribute to include it in the JSON representation
            if "service_type" in dct:
                raise TypeError(
                    "`service_type` is a reserved attribute name for BaseService "
                    "subclasses"
                )
            dct.setdefault("__annotations__", dict())[
                "service_type"
            ] = ServiceType
            dct["service_type"] = Field(service_type, allow_mutation=False)

        cls = cast(Type["BaseService"], super().__new__(mcs, name, bases, dct))

        # register only classes of concrete service implementations
        if service_type:
            # register the service type in the service registry
            ServiceRegistry().register_service_type(cls)
        return cls

    def __call__(cls, *args: Any, **kwargs: Any) -> "BaseServiceMeta":
        """Validate the creation of a service."""
        if not getattr(cls, "SERVICE_TYPE", None):
            raise AttributeError(
                f"Untyped service instances are not allowed. Please set the "
                f"SERVICE_TYPE class attribute for {cls}."
            )
        uuid = kwargs.get("uuid", None)
        if uuid:
            if isinstance(uuid, str):
                uuid = UUID(uuid)
            if not isinstance(uuid, UUID):
                raise ValueError(
                    f"The `uuid` argument for {cls} must be a UUID instance or a "
                    f"string representation of a UUID."
                )

            # if a service instance with the same UUID is already registered,
            # return the existing instance rather than the newly created one
            existing_service = ServiceRegistry().get_service(uuid)
            if existing_service:
                logger.debug(
                    f"Reusing existing service '{existing_service}' "
                    f"instead of creating a new service with the same UUID."
                )
                return cast("BaseServiceMeta", existing_service)

        svc = cast("BaseService", super().__call__(*args, **kwargs))
        ServiceRegistry().register_service(svc)
        return cast("BaseServiceMeta", svc)


class BaseService(BaseTypedModel, metaclass=BaseServiceMeta):
    """Base service class

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

    uuid: UUID = Field(default_factory=uuid4, allow_mutation=False)
    admin_state: ServiceState = ServiceState.INACTIVE
    config: ServiceConfig
    status: ServiceStatus
    # TODO [ENG-703]: allow multiple endpoints per service
    endpoint: Optional[BaseServiceEndpoint]

    def __init__(
        self,
        **attrs: Any,
    ) -> None:
        super().__init__(**attrs)
        self.config.name = self.config.name or self.__class__.__name__

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
            A generator that can be acccessed to get the service logs.
        """

    def update_status(self) -> None:
        """Check the current operational state of the external service
        and update the local operational status information to reflect it.

        This method should be overridden by subclasses that implement
        concrete service status tracking functionality.
        """
        logger.debug(
            "Running status check for service '%s' ...",
            self,
        )
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

    def get_service_status_message(self) -> str:
        """Get a message providing information about the current operational
        state of the service."""
        return (
            f"  Administrative state: `{self.admin_state.value}`\n"
            f"  Operational state: `{self.status.state.value}`\n"
            f"  Last status message: '{self.status.last_error}'\n"
        )

    def poll_service_status(self, timeout: int = 0) -> bool:
        """Poll the external service status until the service operational
        state matches the administrative state, the service enters a failed
        state, or the timeout is reached.

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
        """Provisions resources to run the service."""
        raise NotImplementedError(
            f"Provisioning resources not implemented for {self}."
        )

    def deprovision(self, force: bool = False) -> None:
        """Deprovisions all resources used by the service."""
        raise NotImplementedError(
            f"Deprovisioning resources not implemented for {self}."
        )

    def update(self, config: ServiceConfig) -> None:
        """Update the service configuration.

        Args:
            config: the new service configuration.
        """
        self.config = config

    def start(self, timeout: int = 0) -> None:
        """Start the service and optionally wait for it to become active.

        Args:
            timeout: amount of time to wait for the service to become active.
                If set to 0, the method will return immediately after checking
                the service status.

        Raises:
            RuntimeError: if the service cannot be started
        """
        with console.status(f"Starting service '{self}'.\n"):
            self.admin_state = ServiceState.ACTIVE
            self.provision()
            if timeout > 0:
                if not self.poll_service_status(timeout):
                    raise RuntimeError(
                        f"Failed to start service {self}\n"
                        + self.get_service_status_message()
                    )

    def stop(self, timeout: int = 0, force: bool = False) -> None:
        """Stop the service and optionally wait for it to shutdown.

        Args:
            timeout: amount of time to wait for the service to shutdown.
                If set to 0, the method will return immediately after checking
                the service status.

        Raises:
            RuntimeError: if the service cannot be stopped
        """
        with console.status(f"Stopping service '{self}'.\n"):
            self.admin_state = ServiceState.INACTIVE
            self.deprovision(force)
            if timeout > 0:
                self.poll_service_status(timeout)
                if not self.is_stopped:
                    raise RuntimeError(
                        f"Failed to stop service {self}. Last state: "
                        f"'{self.status.state.value}'. Last error: "
                        f"'{self.status.last_error}'"
                    )

    def __repr__(self) -> str:
        """String representation of the service."""
        return f"{self.__class__.__qualname__}[{self.uuid}] (type: {self.SERVICE_TYPE.type}, flavor: {self.SERVICE_TYPE.flavor})"

    def __str__(self) -> str:
        """String representation of the service."""
        return self.__repr__()

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
