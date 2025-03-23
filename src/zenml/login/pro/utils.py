#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""ZenML Pro login utils."""

from zenml.logger import get_logger
from zenml.login.credentials import ServerType
from zenml.login.credentials_store import get_credentials_store
from zenml.login.pro.client import ZenMLProClient
from zenml.login.pro.constants import ZENML_PRO_API_URL
from zenml.login.pro.workspace.models import WorkspaceStatus

logger = get_logger(__name__)


def get_troubleshooting_instructions(url: str) -> str:
    """Get troubleshooting instructions for a given ZenML Pro server URL.

    Args:
        url: ZenML Pro server URL

    Returns:
        Troubleshooting instructions
    """
    credentials_store = get_credentials_store()

    credentials = credentials_store.get_credentials(url)
    pro_api_url = None
    if credentials and credentials.type == ServerType.PRO:
        pro_api_url = credentials.pro_api_url or ZENML_PRO_API_URL

    if pro_api_url and credentials_store.has_valid_pro_authentication(
        pro_api_url
    ):
        client = ZenMLProClient(pro_api_url)

        try:
            servers = client.workspace.list(url=url, member_only=False)
        except Exception as e:
            logger.debug(f"Failed to list workspaces: {e}")
        else:
            if servers:
                server = servers[0]
                if server.status == WorkspaceStatus.AVAILABLE:
                    return (
                        f"The '{server.name}' ZenML Pro server that the client "
                        "is connected to is currently running but you may not "
                        "have the necessary permissions to access it. Please "
                        "contact your ZenML Pro administrator for more "
                        "information or try to manage the server members "
                        "yourself if you have the necessary permissions by "
                        f"visiting the ZenML Pro workspace page at {server.dashboard_url}."
                    )
                if server.status == WorkspaceStatus.DEACTIVATED:
                    return (
                        f"The '{server.name}' ZenML Pro server that the client "
                        "is connected to has been deactivated. "
                        "Please contact your ZenML Pro administrator for more "
                        "information or to reactivate the server yourself if "
                        "you have the necessary permissions by visiting the "
                        f"ZenML Pro Organization page at {server.dashboard_organization_url}."
                    )
                if server.status == WorkspaceStatus.PENDING:
                    return (
                        f"The '{server.name}' ZenML Pro server that the client "
                        "is connected to is currently undergoing maintenance "
                        "(e.g. being deployed, upgraded or re-activated). "
                        "Please try again later or contact your ZenML Pro "
                        "administrator for more information. You can also "
                        f"visit the ZenML Pro workspace page at {server.dashboard_url}."
                    )
                return (
                    f"The '{server.name}' ZenML Pro server that the client "
                    "is connected to is currently in a failed "
                    "state. Please contact your ZenML Pro administrator for "
                    "more information or try to re-deploy the server "
                    "yourself if you have the necessary permissions by "
                    "visiting the ZenML Pro Organization page at "
                    f"{server.dashboard_organization_url}."
                )

            return (
                f"The ZenML Pro server at URL '{url}' that the client is "
                "connected to does not exist or you may not have access to it. "
                "Please check the URL and your permissions and try again or "
                "connect your client to a different server by running `zenml "
                "login` or by using a service account API key."
            )

    return (
        f"The ZenML Pro server at URL '{url}' that the client is connected to "
        "does not exist, is not running, or you do not have permissions to "
        "connect to it. Please check the URL and your permissions "
        "and try again. The ZenML Pro server might have been deactivated or is "
        "currently pending maintenance. Please contact your ZenML Pro "
        "administrator for more information or try to manage the server "
        "state by visiting the ZenML Pro dashboard."
    )
