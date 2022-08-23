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
"""Zen Server base deployer definition."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from zenml.logger import get_logger
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME

logger = get_logger(__name__)


class BaseServerDeploymentStatus(BaseModel):
    """Base server deployment status.

    Ideally this should convey the following information:

    * whether the server's deployment is managed by this client (i.e. if
    the server was deployed with `zenml up`)
    * for a managed deployment, the status of the deployment/tear-down, e.g.
    not deployed, deploying, running, deleting, deployment timeout/error,
    tear-down timeout/error etc.
    * for an unmanaged deployment, the operational status (i.e. whether the
    server is reachable)

    Attributes:
    """

    deployed: bool
    connected: bool
    last_error: Optional[str] = None


class BaseServerDeploymentConfig(BaseModel):
    """Base server deployment configuration.

    Attributes:
        name: Name of the server deployment.
        username: Default username to use for the server deployment.
        password: Default password to use for the server deployment.
    """

    name: str
    username: str = DEFAULT_USERNAME
    password: str = ""


class BaseServerDeployment(BaseModel):
    """Base server deployment.

    Attributes:
        id: The unique server deployment identifier.
    """

    id: UUID = Field(default_factory=uuid4)
    config: BaseServerDeploymentConfig
    status: BaseServerDeploymentStatus


class BaseServerDeployer(ABC):
    """Base ZenML server deployer class.

    All ZenML server deployers must extend and implement this base class.
    """

    PROVIDER: ClassVar[str]

    @abstractmethod
    def up(
        self,
        config: BaseServerDeploymentConfig,
        connect: bool = True,
        timeout: Optional[int] = None,
    ) -> None:
        """Deploy a ZenML server instance.

        Args:
            config: The server deployment configuration.
            connect: Set to connect to the server after deployment.
            timeout: The timeout in seconds to wait until the deployment is
                successful. If not supplied, the default timeout value is
                implementation specific.
        """

    @abstractmethod
    def down(
        self,
        server: str,
        timeout: Optional[int] = None,
    ) -> None:
        """Tear down a ZenML server instance.

        Args:
            server: The server deployment name or identifier.
            timeout: The timeout in seconds to wait until the deployment is
                torn down. If not supplied, the default timeout value is
                implementation specific.
        """

    @abstractmethod
    def status(self, server: str) -> BaseServerDeploymentStatus:
        """Get the status of a ZenML server instance.

        Args:
            server: The server deployment name or identifier.

        Returns:
            The server deployment status.
        """

    @abstractmethod
    def connect(self, server: str, username: str, password: str) -> None:
        """Connect to a ZenML server instance.

        Create a new ZenML profile and connect it to the indicated ZenML server
        instance.

        Args:
            server: The server deployment name, identifier or URL.
            username: The username to use for the connection.
            password: The password to use for the connection.
        """

    @abstractmethod
    def disconnect(self, server: str) -> None:
        """Disconnect from a ZenML server instance.

        Args:
            server: The server deployment name, identifier or URL.
        """

    @abstractmethod
    def get(self, server: str) -> BaseServerDeployment:
        """Get a server deployment.

        Args:
            server: The server deployment name, identifier or URL.

        Returns:
            The requested server deployment.
        """

    @abstractmethod
    def list(self) -> List[BaseServerDeployment]:
        """List all server deployments.

        Returns:
            The list of server deployments.
        """
