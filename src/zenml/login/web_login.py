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
"""ZenML OAuth2 device authorization grant client support."""

import platform
import time
import webbrowser
from typing import Optional, Union

import requests

from zenml import __version__
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    API,
    AUTH,
    DEFAULT_HTTP_TIMEOUT,
    DEVICE_AUTHORIZATION,
    LOGIN,
    VERSION_1,
)
from zenml.exceptions import AuthorizationException, OAuthError
from zenml.logger import get_logger
from zenml.login.credentials import APIToken
from zenml.login.pro.constants import ZENML_PRO_API_URL

logger = get_logger(__name__)


def web_login(
    url: Optional[str] = None,
    verify_ssl: Optional[Union[str, bool]] = None,
    pro_api_url: Optional[str] = None,
) -> APIToken:
    """Implements the OAuth2 Device Authorization Grant flow.

    This function implements the client side of the OAuth2 Device Authorization
    Grant flow as defined in https://tools.ietf.org/html/rfc8628, with the
    following customizations:

    * the unique ZenML client ID (`user_id` in the global config) is used
    as the OAuth2 client ID value
    * additional information is added to the user agent header to be used by
    users to identify the ZenML client

    Upon completion of the flow, the access token is saved in the credentials store.

    Args:
        url: The URL of the OAuth2 server. If not provided, the ZenML Pro API
            server is used by default.
        verify_ssl: Whether to verify the SSL certificate of the OAuth2 server.
            If a string is passed, it is interpreted as the path to a CA bundle
            file.
        pro_api_url: The URL of the ZenML Pro API server. If not provided, the
            default ZenML Pro API server URL is used.

    Returns:
        The response returned by the OAuth2 server.

    Raises:
        AuthorizationException: If an error occurred during the authorization
            process.
    """
    from zenml.login.credentials_store import get_credentials_store
    from zenml.models import (
        OAuthDeviceAuthorizationRequest,
        OAuthDeviceAuthorizationResponse,
        OAuthDeviceTokenRequest,
        OAuthDeviceUserAgentHeader,
        OAuthTokenResponse,
    )

    credentials_store = get_credentials_store()

    # Make a request to the OAuth2 server to get the device code and user code.
    # The client ID used for the request is the unique ID of the ZenML client.
    response: Optional[requests.Response] = None

    # Add the following information in the user agent header to be used by users
    # to identify the ZenML client:
    #
    # * the ZenML version
    # * the python version
    # * the OS type
    # * the hostname
    #
    user_agent_header = OAuthDeviceUserAgentHeader(
        hostname=platform.node(),
        zenml_version=__version__,
        python_version=platform.python_version(),
        os=platform.system(),
    )

    zenml_pro = False
    if not url:
        # If no URL is provided, we use the ZenML Pro API server by default
        zenml_pro = True
        url = base_url = pro_api_url or ZENML_PRO_API_URL
    else:
        # Get rid of any trailing slashes to prevent issues when having double
        # slashes in the URL
        url = url.rstrip("/")
        if pro_api_url:
            # This is a ZenML Pro server. The device authentication is done
            # through the ZenML Pro API.
            zenml_pro = True
            base_url = pro_api_url
        else:
            base_url = url

    auth_request = OAuthDeviceAuthorizationRequest(
        client_id=GlobalConfiguration().user_id
    )

    # If an existing token is found in the credentials store, we reuse its
    # device ID to avoid creating a new device ID for the same device.
    existing_token = credentials_store.get_token(url)
    if existing_token and existing_token.device_id:
        auth_request.device_id = existing_token.device_id

    if zenml_pro:
        auth_url = base_url + AUTH + DEVICE_AUTHORIZATION
        login_url = base_url + AUTH + LOGIN
    else:
        auth_url = base_url + API + VERSION_1 + DEVICE_AUTHORIZATION
        login_url = base_url + API + VERSION_1 + LOGIN

    try:
        response = requests.post(
            auth_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": user_agent_header.encode(),
            },
            data=auth_request.model_dump(exclude_none=True),
            verify=verify_ssl,
            timeout=DEFAULT_HTTP_TIMEOUT,
        )
        if response.status_code == 200:
            auth_response = OAuthDeviceAuthorizationResponse(**response.json())
        else:
            logger.info(f"Error: {response.status_code} {response.text}")
            raise AuthorizationException(
                f"Could not connect to {base_url}. Please check the URL."
            )
    except (requests.exceptions.JSONDecodeError, ValueError, TypeError):
        logger.exception("Bad response received from API server.")
        raise AuthorizationException(
            "Bad response received from API server. Please check the URL."
        )
    except requests.exceptions.RequestException:
        logger.exception("Could not connect to API server.")
        raise AuthorizationException(
            f"Could not connect to {base_url}. Please check the URL."
        )

    # Open the verification URL in the user's browser
    verification_uri = (
        auth_response.verification_uri_complete
        or auth_response.verification_uri
    )
    if verification_uri.startswith("/"):
        # If the verification URI is a relative path, we need to add the base
        # URL to it
        verification_uri = base_url + verification_uri
    webbrowser.open(verification_uri)
    logger.info(
        f"If your browser did not open automatically, please open the "
        f"following URL into your browser to proceed with the authentication:"
        f"\n\n{verification_uri}\n"
    )

    # Poll the OAuth2 server until the user has authorized the device
    token_request = OAuthDeviceTokenRequest(
        device_code=auth_response.device_code,
        client_id=auth_request.client_id,
    )
    expires_in = auth_response.expires_in
    interval = auth_response.interval
    token_response: OAuthTokenResponse
    while True:
        response = requests.post(
            login_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=token_request.model_dump(),
            verify=verify_ssl,
            timeout=DEFAULT_HTTP_TIMEOUT,
        )
        if response.status_code == 200:
            # The user has authorized the device, so we can extract the access token
            token_response = OAuthTokenResponse(**response.json())
            if zenml_pro:
                logger.info("Successfully logged in to ZenML Pro.")
            else:
                logger.info(f"Successfully logged in to {url}.")
            break
        elif response.status_code == 400:
            try:
                error_response = OAuthError(**response.json())
            except (
                requests.exceptions.JSONDecodeError,
                ValueError,
                TypeError,
            ):
                raise AuthorizationException(
                    f"Error received from {base_url}: {response.text}"
                )

            if error_response.error == "authorization_pending":
                # The user hasn't authorized the device yet, so we wait for the
                # interval and try again
                pass
            elif error_response.error == "slow_down":
                # The OAuth2 server is asking us to slow down our polling
                interval += 5
            else:
                # There was another error with the request
                raise AuthorizationException(
                    f"Error: {error_response.error} {error_response.error_description}"
                )

            expires_in -= interval
            if expires_in <= 0:
                raise AuthorizationException(
                    "User did not authorize the device in time."
                )
            time.sleep(interval)
        else:
            # There was another error with the request
            raise AuthorizationException(
                f"Error: {response.status_code} {response.text}"
            )

    # Save the token in the credentials store
    return credentials_store.set_token(
        url, token_response, is_zenml_pro=zenml_pro
    )
