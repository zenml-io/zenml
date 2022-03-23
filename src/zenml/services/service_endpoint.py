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

from typing import Any, Optional, Tuple

from zenml.logger import get_logger
from zenml.services.service_monitor import BaseServiceEndpointHealthMonitor
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.utils.enum_utils import StrEnum
from zenml.utils.typed_model import BaseTypedModel

logger = get_logger(__name__)


class ServiceEndpointProtocol(StrEnum):
    """Possible endpoint protocol values."""

    TCP = "tcp"
    HTTP = "http"
    HTTPS = "https"


class ServiceEndpointConfig(BaseTypedModel):
    """Generic service endpoint configuration.

    Concrete service classes should extend this class and add additional
    attributes that they want to see reflected and use in the endpoint
    configuration.

    Attributes:
        name: unique name for the service endpoint
        description: description of the service endpoint
    """

    name: str = ""
    description: str = ""


class ServiceEndpointStatus(ServiceStatus):
    """Status information describing the operational state of a service
    endpoint (e.g. a HTTP/HTTPS API or generic TCP endpoint exposed by a
    service).

    Concrete service classes should extend this class and add additional
    attributes that make up the operational state of the service endpoint.

    Attributes:
        protocol: the TCP protocol used by the service endpoint
        hostname: the hostname where the service endpoint is accessible
        port: the current TCP port where the service endpoint is accessible
    """

    protocol: ServiceEndpointProtocol = ServiceEndpointProtocol.TCP
    hostname: Optional[str] = None
    port: Optional[int] = None

    @property
    def uri(self) -> Optional[str]:
        """Get the URI of the service endpoint.

        Returns:
            The URI of the service endpoint or None, if the service endpoint
            operational status doesn't have the required information.
        """
        if not self.hostname or not self.port or not self.protocol:
            # the service is not yet in a state in which the endpoint hostname
            # port and protocol are known
            return None

        return f"{self.protocol.value}://{self.hostname}:{self.port}/"


class BaseServiceEndpoint(BaseTypedModel):
    """Base service class

    This class implements generic functionality concerning the life-cycle
    management and tracking of an external service endpoint (e.g. a HTTP/HTTPS
    API or generic TCP endpoint exposed by a service).

    Attributes:
        admin_state: the administrative state of the service endpoint
        config: service endpoint configuration
        status: service endpoint status
        monitor: optional service endpoint health monitor
    """

    admin_state: ServiceState = ServiceState.INACTIVE
    config: ServiceEndpointConfig
    status: ServiceEndpointStatus
    # TODO [ENG-701]: allow multiple monitors per endpoint
    monitor: Optional[BaseServiceEndpointHealthMonitor] = None

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.config.name = self.config.name or self.__class__.__name__

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the external
        service endpoint.

        Returns:
            The operational state of the external service endpoint and a
            message providing additional information about that state
            (e.g. a description of the error, if one is encountered while
            checking the service status).
        """
        if not self.monitor:
            # no health monitor configured; assume service operational state
            # always matches the admin state
            return self.admin_state, ""
        return self.monitor.check_endpoint_status(self)

    def update_status(self) -> None:
        """Check the the current operational state of the external service
        endpoint and update the local operational status information
        accordingly.
        """
        logger.debug(
            "Running health check for service endpoint '%s' ...",
            self.config.name,
        )
        state, err = self.check_status()
        logger.debug(
            "Health check results for service endpoint '%s': %s [%s]",
            self.config.name,
            state.name,
            err,
        )
        self.status.update_state(state, err)

    def is_active(self) -> bool:
        """Check if the service endpoint is active (i.e. is responsive and can
        receive requests).

        This method will use the configured health monitor to actively check the
        endpoint status and will return the result.

        Returns:
            True if the service endpoint is active, otherwise False.
        """
        self.update_status()
        return self.status.state == ServiceState.ACTIVE

    def is_inactive(self) -> bool:
        """Check if the service endpoint is inactive (i.e. is not responsive and
        cannot receive requests).

        This method will use the configured health monitor to actively check the
        endpoint status and will return the result.

        Returns:
            True if the service endpoint is inactive, otherwise False.
        """
        self.update_status()
        return self.status.state == ServiceState.INACTIVE
