#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Utility functions for ZenML servers."""

from typing import TYPE_CHECKING, Optional

from zenml.constants import API, VERSION_1

if TYPE_CHECKING:
    from zenml.zen_server.deploy import LocalServerDeployment


def get_server_api_url() -> Optional[str]:
    """Get the externally reachable base URL of the ZenML server API.

    Returns:
        The absolute API URL, or `None` when the server has no externally
        reachable URL configured.
    """
    from zenml.config.server_config import ServerConfiguration

    config = ServerConfiguration.get_server_config()
    if not config.server_url:
        return None

    segments = [
        config.server_url.rstrip("/"),
        config.root_url_path.strip("/"),
        API.strip("/"),
        VERSION_1.strip("/"),
    ]
    return "/".join(segment for segment in segments if segment)


def get_local_server() -> Optional["LocalServerDeployment"]:
    """Get the active local server.

    Call this function to retrieve the local server deployed on this machine.

    Returns:
        The local server deployment or None, if no local server deployment was
        found.
    """
    from zenml.zen_server.deploy.deployer import LocalServerDeployer
    from zenml.zen_server.deploy.exceptions import (
        ServerDeploymentNotFoundError,
    )

    deployer = LocalServerDeployer()
    try:
        return deployer.get_server()
    except ServerDeploymentNotFoundError:
        return None


def connected_to_local_server() -> bool:
    """Check if the client is connected to a local server.

    Returns:
        True if the client is connected to a local server, False otherwise.
    """
    from zenml.zen_server.deploy.deployer import LocalServerDeployer

    deployer = LocalServerDeployer()
    return deployer.is_connected_to_server()
