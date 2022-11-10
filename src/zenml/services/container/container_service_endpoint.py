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
"""Implementation of a containerized service endpoint."""

from typing import Optional, Union

from pydantic import Field

from zenml.constants import DEFAULT_LOCAL_SERVICE_IP_ADDRESS
from zenml.logger import get_logger
from zenml.services.service_endpoint import (
    BaseServiceEndpoint,
    ServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceEndpointStatus,
)
from zenml.services.service_monitor import (
    HTTPEndpointHealthMonitor,
    TCPEndpointHealthMonitor,
)
from zenml.utils.networking_utils import port_available, scan_for_available_port

logger = get_logger(__name__)


class ContainerServiceEndpointConfig(ServiceEndpointConfig):
    """Local daemon service endpoint configuration.

    Attributes:
        protocol: the TCP protocol implemented by the service endpoint
        port: preferred TCP port value for the service endpoint. If the port
            is in use when the service is started, setting `allocate_port` to
            True will also try to allocate a new port value, otherwise an
            exception will be raised.
        allocate_port: set to True to allocate a free TCP port for the
            service endpoint automatically.
    """

    protocol: ServiceEndpointProtocol = ServiceEndpointProtocol.TCP
    port: Optional[int] = None
    allocate_port: bool = True


class ContainerServiceEndpointStatus(ServiceEndpointStatus):
    """Local daemon service endpoint status."""


class ContainerServiceEndpoint(BaseServiceEndpoint):
    """A service endpoint exposed by a containerized process.

    This class extends the base service endpoint class with functionality
    concerning the life-cycle management and tracking of endpoints exposed
    by external services implemented as containerized processes.

    Attributes:
        config: service endpoint configuration
        status: service endpoint status
        monitor: optional service endpoint health monitor
    """

    config: ContainerServiceEndpointConfig = Field(
        default_factory=ContainerServiceEndpointConfig
    )
    status: ContainerServiceEndpointStatus = Field(
        default_factory=ContainerServiceEndpointStatus
    )
    monitor: Optional[
        Union[HTTPEndpointHealthMonitor, TCPEndpointHealthMonitor]
    ] = Field(..., discriminator="type")

    def _lookup_free_port(self) -> int:
        """Search for a free TCP port for the service endpoint.

        If a preferred TCP port value is explicitly requested through the
        endpoint configuration, it will be checked first. If a port was
        previously used the last time the service was running (i.e. as
        indicated in the service endpoint status), it will be checked next for
        availability.

        As a last resort, this call will search for a free TCP port, if
        `allocate_port` is set to True in the endpoint configuration.

        Returns:
            An available TCP port number

        Raises:
            IOError: if the preferred TCP port is busy and `allocate_port` is
                disabled in the endpoint configuration, or if no free TCP port
                could be otherwise allocated.
        """
        # If a port value is explicitly configured, attempt to use it first
        if self.config.port:
            if port_available(self.config.port):
                return self.config.port
            if not self.config.allocate_port:
                raise IOError(f"TCP port {self.config.port} is not available.")

        # Attempt to reuse the port used when the services was last running
        if self.status.port and port_available(self.status.port):
            return self.status.port

        port = scan_for_available_port()
        if port:
            return port
        raise IOError("No free TCP ports found")

    def prepare_for_start(self) -> None:
        """Prepare the service endpoint for starting.

        This method is called before the service is started.
        """
        self.status.protocol = self.config.protocol
        self.status.port = self._lookup_free_port()
        # Container endpoints are always exposed on the local host
        self.status.hostname = DEFAULT_LOCAL_SERVICE_IP_ADDRESS
