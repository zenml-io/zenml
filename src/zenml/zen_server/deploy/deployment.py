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
"""Zen Server deployment definitions."""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from zenml.enums import ServerProviderType
from zenml.services.service_status import ServiceState


class LocalServerDeploymentConfig(BaseModel):
    """Generic local server deployment configuration.

    All local server deployment configurations should inherit from this class
    and handle extra attributes as provider specific attributes.

    Attributes:
        provider: The server provider type.
    """

    provider: ServerProviderType

    @property
    def url(self) -> Optional[str]:
        """Get the configured server URL.

        Returns:
            The configured server URL.
        """
        return None

    model_config = ConfigDict(
        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment=True,
        # Allow extra attributes to be set in the base class. The concrete
        # classes are responsible for validating the attributes.
        extra="allow",
    )


class LocalServerDeploymentStatus(BaseModel):
    """Local server deployment status.

    Ideally this should convey the following information:

    * whether the server's deployment is managed by this client (i.e. if
    the server was deployed with `zenml up`)
    * for a managed deployment, the status of the deployment/tear-down, e.g.
    not deployed, deploying, running, deleting, deployment timeout/error,
    tear-down timeout/error etc.
    * for an unmanaged deployment, the operational status (i.e. whether the
    server is reachable)
    * the URL of the server

    Attributes:
        status: The status of the server deployment.
        status_message: A message describing the last status.
        connected: Whether the client is currently connected to this server.
        url: The URL of the server.
    """

    status: ServiceState
    status_message: Optional[str] = None
    connected: bool
    url: Optional[str] = None
    ca_crt: Optional[str] = None


class LocalServerDeployment(BaseModel):
    """Server deployment.

    Attributes:
        config: The server deployment configuration.
        status: The server deployment status.
    """

    config: LocalServerDeploymentConfig
    status: Optional[LocalServerDeploymentStatus] = None

    @property
    def is_running(self) -> bool:
        """Check if the server is running.

        Returns:
            Whether the server is running.
        """
        return (
            self.status is not None
            and self.status.status == ServiceState.ACTIVE
        )
