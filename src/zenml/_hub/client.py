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
"""Client for the ZenML Hub."""
import os
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

import requests

from zenml._hub.constants import (
    ZENML_HUB_ADMIN_USERNAME,
    ZENML_HUB_CLIENT_TIMEOUT,
    ZENML_HUB_CLIENT_VERIFY,
    ZENML_HUB_DEFAULT_URL,
)
from zenml.analytics import source_context
from zenml.client import Client
from zenml.constants import ENV_ZENML_HUB_URL, IS_DEBUG_ENV
from zenml.logger import get_logger
from zenml.models import (
    HubPluginRequestModel,
    HubPluginResponseModel,
    HubUserResponseModel,
)

logger = get_logger(__name__)


class HubAPIError(Exception):
    """Exception raised when the Hub returns an error or unexpected response."""


class HubClient:
    """Client for the ZenML Hub."""

    def __init__(self, url: Optional[str] = None) -> None:
        """Initialize the client.

        Args:
            url: The URL of the ZenML Hub.
        """
        self.url = url or self.get_default_url()
        self.auth_token = Client().active_user.hub_token

    @staticmethod
    def get_default_url() -> str:
        """Get the default URL of the ZenML Hub.

        Returns:
            The default URL of the ZenML Hub.
        """
        return os.getenv(ENV_ZENML_HUB_URL, default=ZENML_HUB_DEFAULT_URL)

    def list_plugins(self, **params: Any) -> List[HubPluginResponseModel]:
        """List all plugins in the hub.

        Args:
            **params: The query parameters to send in the request.

        Returns:
            The list of plugin response models.
        """
        response = self._request("GET", "/plugins", params=params)
        if not isinstance(response, list):
            return []
        return [
            HubPluginResponseModel.parse_obj(plugin) for plugin in response
        ]

    def get_plugin(
        self,
        name: str,
        version: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Optional[HubPluginResponseModel]:
        """Get a specific plugin from the hub.

        Args:
            name: The name of the plugin.
            version: The version of the plugin. If not specified, the latest
                version will be returned.
            author: Username of the author of the plugin.

        Returns:
            The plugin response model or None if the plugin does not exist.
        """
        route = "/plugins"
        if not author:
            author = ZENML_HUB_ADMIN_USERNAME
        options = [
            f"name={name}",
            f"username={author}",
        ]
        if version:
            options.append(f"version={version}")
        if options:
            route += "?" + "&".join(options)
        try:
            response = self._request("GET", route)
        except HubAPIError:
            return None
        if not isinstance(response, list) or len(response) == 0:
            return None
        return HubPluginResponseModel.parse_obj(response[0])

    def create_plugin(
        self, plugin_request: HubPluginRequestModel
    ) -> HubPluginResponseModel:
        """Create a plugin in the hub.

        Args:
            plugin_request: The plugin request model.

        Returns:
            The plugin response model.
        """
        route = "/plugins"
        response = self._request("POST", route, data=plugin_request.json())
        return HubPluginResponseModel.parse_obj(response)

    # TODO: Potentially reenable this later if hub adds logs streaming endpoint
    # def stream_plugin_build_logs(
    #     self, plugin_name: str, plugin_version: str
    # ) -> bool:
    #     """Stream the build logs of a plugin.

    #     Args:
    #         plugin_name: The name of the plugin.
    #         plugin_version: The version of the plugin. If not specified, the
    #             latest version will be used.

    #     Returns:
    #         Whether any logs were found.

    #     Raises:
    #         HubAPIError: If the build failed.
    #     """
    #     route = f"plugins/{plugin_name}/versions/{plugin_version}/logs"
    #     logs_url = os.path.join(self.url, route)

    #     found_logs = False
    #     with requests.get(logs_url, stream=True) as response:
    #         for line in response.iter_lines(
    #             chunk_size=None, decode_unicode=True
    #         ):
    #             found_logs = True
    #             if line.startswith("Build failed"):
    #                 raise HubAPIError(line)
    #             else:
    #                 logger.info(line)
    #     return found_logs

    def login(self, username: str, password: str) -> None:
        """Login to the ZenML Hub.

        Args:
            username: The username of the user in the ZenML Hub.
            password: The password of the user in the ZenML Hub.

        Raises:
            HubAPIError: If the login failed.
        """
        route = "/auth/jwt/login"
        response = self._request(
            method="POST",
            route=route,
            data={"username": username, "password": password},
            content_type="application/x-www-form-urlencoded",
        )
        if isinstance(response, dict):
            auth_token = response.get("access_token")
            if auth_token:
                self.set_auth_token(str(auth_token))
                return
        raise HubAPIError(f"Unexpected response: {response}")

    def set_auth_token(self, auth_token: Optional[str]) -> None:
        """Set the auth token.

        Args:
            auth_token: The auth token to set.
        """
        client = Client()
        client.update_user(
            name_id_or_prefix=client.active_user.id,
            updated_hub_token=auth_token,
        )
        self.auth_token = auth_token

    def get_github_login_url(self) -> str:
        """Get the GitHub login URL.

        Returns:
            The GitHub login URL.

        Raises:
            HubAPIError: If the request failed.
        """
        route = "/auth/github/authorize"
        response = self._request("GET", route)
        if isinstance(response, dict):
            auth_url = response.get("authorization_url")
            if auth_url:
                return str(auth_url)
        raise HubAPIError(f"Unexpected response: {str(response)}")

    def get_me(self) -> Optional[HubUserResponseModel]:
        """Get the current user.

        Returns:
            The user response model or None if the user does not exist.
        """
        try:
            response = self._request("GET", "/users/me")
            return HubUserResponseModel.parse_obj(response)
        except HubAPIError:
            return None

    def _request(
        self,
        method: str,
        route: str,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        content_type: str = "application/json",
    ) -> Any:
        """Helper function to make a request to the hub.

        Args:
            method: The HTTP method to use.
            route: The route to send the request to, e.g., "/plugins".
            data: The data to send in the request.
            params: The query parameters to send in the request.
            content_type: The content type of the request.

        Returns:
            The response JSON.

        Raises:
            HubAPIError: If the request failed.
        """
        session = requests.Session()

        # Define headers
        headers = {
            "Accept": "application/json",
            "Content-Type": content_type,
            "Debug-Context": str(IS_DEBUG_ENV),
            "Source-Context": str(source_context.get().value),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        # Make the request
        route = route.lstrip("/")
        endpoint_url = os.path.join(self.url, route)
        response = session.request(
            method=method,
            url=endpoint_url,
            data=data,
            headers=headers,
            params=params,
            verify=ZENML_HUB_CLIENT_VERIFY,
            timeout=ZENML_HUB_CLIENT_TIMEOUT,
        )

        # Parse and return the response
        if 200 <= response.status_code < 300:
            return response.json()
        try:
            error_msg = response.json().get("detail", response.text)
        except JSONDecodeError:
            error_msg = response.text
        raise HubAPIError(f"Request to ZenML Hub failed: {error_msg}")
