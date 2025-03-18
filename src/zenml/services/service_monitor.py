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
"""Implementation of the service health monitor."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple

import requests
from pydantic import Field

from zenml.enums import ServiceState
from zenml.logger import get_logger
from zenml.utils.networking_utils import port_is_open
from zenml.utils.typed_model import BaseTypedModel

logger = get_logger(__name__)


if TYPE_CHECKING:
    from zenml.services.service_endpoint import BaseServiceEndpoint


DEFAULT_HTTP_HEALTHCHECK_TIMEOUT = 5


class ServiceEndpointHealthMonitorConfig(BaseTypedModel):
    """Generic service health monitor configuration.

    Concrete service classes should extend this class and add additional
    attributes that they want to see reflected and use in the health monitor
    configuration.
    """


class BaseServiceEndpointHealthMonitor(BaseTypedModel):
    """Base class used for service endpoint health monitors.

    Attributes:
        config: health monitor configuration for endpoint
    """

    config: ServiceEndpointHealthMonitorConfig = Field(
        default_factory=ServiceEndpointHealthMonitorConfig
    )

    @abstractmethod
    def check_endpoint_status(
        self, endpoint: "BaseServiceEndpoint"
    ) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the external service endpoint.

        Args:
            endpoint: service endpoint to check

        This method should be overridden by subclasses that implement
        concrete service endpoint tracking functionality.

        Returns:
            The operational state of the external service endpoint and an
            optional error message, if an error is encountered while checking
            the service endpoint status.
        """


class HTTPEndpointHealthMonitorConfig(ServiceEndpointHealthMonitorConfig):
    """HTTP service endpoint health monitor configuration.

    Attributes:
        healthcheck_uri_path: URI subpath to use to perform service endpoint
            healthchecks. If not set, the service endpoint URI will be used
            instead.
        use_head_request: set to True to use a HEAD request instead of a GET
            when calling the healthcheck URI.
        http_status_code: HTTP status code to expect in the health check
            response.
        http_timeout: HTTP health check request timeout in seconds.
    """

    healthcheck_uri_path: str = ""
    use_head_request: bool = False
    http_status_code: int = 200
    http_timeout: int = DEFAULT_HTTP_HEALTHCHECK_TIMEOUT


class HTTPEndpointHealthMonitor(BaseServiceEndpointHealthMonitor):
    """HTTP service endpoint health monitor.

    Attributes:
        config: health monitor configuration for HTTP endpoint
    """

    config: HTTPEndpointHealthMonitorConfig = Field(
        default_factory=HTTPEndpointHealthMonitorConfig
    )

    def get_healthcheck_uri(
        self, endpoint: "BaseServiceEndpoint"
    ) -> Optional[str]:
        """Get the healthcheck URI for the given service endpoint.

        Args:
            endpoint: service endpoint to get the healthcheck URI for

        Returns:
            The healthcheck URI for the given service endpoint or None, if
            the service endpoint doesn't have a healthcheck URI.
        """
        uri = endpoint.status.uri
        if not uri:
            return None
        if not self.config.healthcheck_uri_path:
            return uri
        return (
            f"{uri.rstrip('/')}/{self.config.healthcheck_uri_path.lstrip('/')}"
        )

    def check_endpoint_status(
        self, endpoint: "BaseServiceEndpoint"
    ) -> Tuple[ServiceState, str]:
        """Run a HTTP endpoint API healthcheck.

        Args:
            endpoint: service endpoint to check.

        Returns:
            The operational state of the external HTTP endpoint and an
            optional message describing that state (e.g. an error message,
            if an error is encountered while checking the HTTP endpoint
            status).
        """
        from zenml.services.service_endpoint import ServiceEndpointProtocol

        if endpoint.status.protocol not in [
            ServiceEndpointProtocol.HTTP,
            ServiceEndpointProtocol.HTTPS,
        ]:
            return (
                ServiceState.ERROR,
                "endpoint protocol is not HTTP nor HTTPS.",
            )

        check_uri = self.get_healthcheck_uri(endpoint)
        if not check_uri:
            return ServiceState.ERROR, "no HTTP healthcheck URI available"

        logger.debug("Running HTTP healthcheck for URI: %s", check_uri)

        try:
            if self.config.use_head_request:
                r = requests.head(
                    check_uri,
                    timeout=self.config.http_timeout,
                )
            else:
                r = requests.get(
                    check_uri,
                    timeout=self.config.http_timeout,
                )
            if r.status_code == self.config.http_status_code:
                # the endpoint is healthy
                return ServiceState.ACTIVE, ""
            error = f"HTTP endpoint healthcheck returned unexpected status code: {r.status_code}"
        except requests.ConnectionError as e:
            error = f"HTTP endpoint healthcheck connection error: {str(e)}"
        except requests.Timeout as e:
            error = f"HTTP endpoint healthcheck request timed out: {str(e)}"
        except requests.RequestException as e:
            error = (
                f"unexpected error encountered while running HTTP endpoint "
                f"healthcheck: {str(e)}"
            )

        return ServiceState.ERROR, error


class TCPEndpointHealthMonitorConfig(ServiceEndpointHealthMonitorConfig):
    """TCP service endpoint health monitor configuration."""


class TCPEndpointHealthMonitor(BaseServiceEndpointHealthMonitor):
    """TCP service endpoint health monitor.

    Attributes:
        config: health monitor configuration for TCP endpoint
    """

    config: TCPEndpointHealthMonitorConfig

    def check_endpoint_status(
        self, endpoint: "BaseServiceEndpoint"
    ) -> Tuple[ServiceState, str]:
        """Run a TCP endpoint healthcheck.

        Args:
            endpoint: service endpoint to check.

        Returns:
            The operational state of the external TCP endpoint and an
            optional message describing that state (e.g. an error message,
            if an error is encountered while checking the TCP endpoint
            status).
        """
        if not endpoint.status.port or not endpoint.status.hostname:
            return (
                ServiceState.ERROR,
                "TCP port and hostname values are not known",
            )

        logger.debug(
            "Running TCP healthcheck for TCP port: %d", endpoint.status.port
        )

        if port_is_open(endpoint.status.hostname, endpoint.status.port):
            # the endpoint is healthy
            return ServiceState.ACTIVE, ""

        return (
            ServiceState.ERROR,
            "TCP endpoint healthcheck error: TCP port is not "
            "open or not accessible",
        )
