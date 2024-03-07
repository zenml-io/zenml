#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Public Python API of ZenML.

Everything defined/imported here should be highly import-optimized so we don't
slow down the CLI.
"""

from typing import Optional

from zenml.logger import get_logger

logger = get_logger(__name__)


def show(
    ngrok_token: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Show the ZenML dashboard.

    Args:
        ngrok_token: An ngrok auth token to use for exposing the ZenML
            dashboard on a public domain. Primarily used for accessing the
            dashboard in Colab.
        username: The username to prefill in the login form.
        password: The password to prefill in the login form.
    """
    from zenml.utils.dashboard_utils import show_dashboard
    from zenml.utils.networking_utils import get_or_create_ngrok_tunnel
    from zenml.zen_server.utils import get_active_server_details

    url, port = get_active_server_details()

    if ngrok_token and port:
        ngrok_url = get_or_create_ngrok_tunnel(
            ngrok_token=ngrok_token, port=port
        )
        logger.debug(f"Tunneling dashboard from {url} to {ngrok_url}.")
        url = ngrok_url

    url = f"{url}:{port}" if port else url
    if username:
        url += f"/login?username={username}"
    if username and password:
        url += f"&password={password}"

    show_dashboard(url)
