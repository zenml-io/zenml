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
"""ZenML login credentials store support."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING,
    handle_bool_env_var,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.login.credentials import APIToken, ServerCredentials, ServerType
from zenml.login.pro.constants import ZENML_PRO_API_URL
from zenml.login.pro.tenant.models import TenantRead
from zenml.models import OAuthTokenResponse, ServerModel
from zenml.utils import yaml_utils
from zenml.utils.singleton import SingletonMetaClass

logger = get_logger(__name__)

CREDENTIALS_STORE_FILENAME = "credentials.yaml"

# How long to keep tokens in the credentials store after their expiration date before evicting them
TOKEN_STORE_EVICTION_TIME = 60 * 60 * 24 * 7  # 1 week


class CredentialsStore(metaclass=SingletonMetaClass):
    """Login credentials store.

    This is a singleton object that maintains a cache of all API tokens and API
    keys that are configured for the ZenML servers that the client connects to
    throughout its lifetime.

    The cache is persistent and it is backed by a `credentials.yaml` YAML file
    kept in the global configuration location. The Credentials Store cache is
    populated mainly in the following ways:

        1. when the user runs `zenml login` to authenticate to a ZenML Pro
        server, the ZenML Pro API token fetched from the web login flow is
        stored in the Credentials Store.
        2. when the user runs `zenml login` to authenticate to a regular ZenML
        server with the web login flow, the ZenML server API token fetched
        through the web login flow is stored in the Credentials Store
        3. when the user runs `zenml login` to authenticate to any ZenML server
        using an API key, the API key is stored in the Credentials Store
        4. when the REST zen store is initialized, it starts up not yet
        authenticated. Then, if/when it needs to authenticate or re-authenticate
        to the remote server, it will use whatever form of credentials it finds
        in the Credentials Store, in order of priority:

            * if it finds an API token that is not expired (e.g. authorized
            device API tokens fetched through the web login flow or short-lived
            session API tokens fetched through some other means of
            authentication), it will use that to authenticate
            * for ZenML servers that use an API key to authenticate, it will use
            that to fetch a short-lived ZenML Pro server API token that it also
            stores in the Credentials Store
            * for ZenML Pro servers, it exchanges the longer-lived ZenML Pro API
            token into a short lived ZenML Pro server API token

    Alongside credentials, the Credentials Store is also used to store
    additional server information:
        * ZenML Pro tenant information populated by the `zenml login` command
        * ZenML server information populated by the REST zen store by fetching
        the server's information endpoint after authenticating

    """

    credentials: Dict[str, ServerCredentials] = {}
    last_modified_time: Optional[float] = None

    def __init__(self) -> None:
        """Initializes the login credentials store with values loaded from the credentials YAML file.

        CredentialsStore is a singleton class: only one instance can exist.
        Calling this constructor multiple times will always yield the same
        instance.
        """
        self._load_credentials()

    @property
    def _credentials_file(self) -> str:
        """Path to the file where the credentials are stored.

        Returns:
            The path to the file where the credentials are stored.
        """
        config_path = GlobalConfiguration().config_directory
        return os.path.join(config_path, CREDENTIALS_STORE_FILENAME)

    def _load_credentials(self) -> None:
        """Load the credentials from the YAML file if it exists."""
        if handle_bool_env_var(ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING):
            return

        credentials_file = self._credentials_file
        credentials_store = {}

        if fileio.exists(credentials_file):
            try:
                credentials_store = yaml_utils.read_yaml(credentials_file)
            except Exception as e:
                logger.error(
                    f"Failed to load credentials file {credentials_file}: {e}. "
                )
            self.last_modified_time = os.path.getmtime(credentials_file)

        if credentials_store is None:
            # This can happen for example if the config file is empty
            credentials_store = {}
        elif not isinstance(credentials_store, dict):
            logger.warning(
                f"The credentials file {credentials_file} is corrupted. "
                "Creating a new credentials file."
            )
            credentials_store = {}

        for server_url, token_data in credentials_store.items():
            try:
                self.credentials[server_url] = ServerCredentials(**token_data)
            except ValueError as e:
                logger.warning(
                    f"Failed to load credentials for {server_url}: {e}. "
                    "Ignoring this token."
                )

    def _save_credentials(self) -> None:
        """Dump the current credentials store to the YAML file."""
        if handle_bool_env_var(ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING):
            return
        credentials_file = self._credentials_file
        credentials_store = {
            server_url: credential.model_dump(
                mode="json", exclude_none=True, exclude_unset=True
            )
            for server_url, credential in self.credentials.items()
            # Evict tokens that have expired past the eviction time
            # and have no API key or username/password to fall back on
            if credential.api_key
            or credential.username
            and credential.password is not None
            or credential.api_token
            and (
                not credential.api_token.expires_at
                or credential.api_token.expires_at
                + timedelta(seconds=TOKEN_STORE_EVICTION_TIME)
                > datetime.now(timezone.utc)
            )
        }
        yaml_utils.write_yaml(credentials_file, credentials_store)
        self.last_modified_time = os.path.getmtime(credentials_file)

    def check_and_reload_from_file(self) -> None:
        """Check if the credentials file has been modified and reload it if necessary."""
        if handle_bool_env_var(ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING):
            return
        if not self.last_modified_time:
            return
        credentials_file = self._credentials_file
        try:
            last_modified_time = os.path.getmtime(credentials_file)
        except FileNotFoundError:
            # The credentials file has been deleted
            self.last_modified_time = None
            return
        if last_modified_time != self.last_modified_time:
            self._load_credentials()

    def get_password(
        self, server_url: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Retrieve the username and password from the credentials store for a specific server URL.

        Args:
            server_url: The server URL for which to retrieve the username and
                password.

        Returns:
            The stored username and password if they exist, None otherwise.
        """
        self.check_and_reload_from_file()
        credential = self.credentials.get(server_url)
        if credential:
            return credential.username, credential.password
        return None, None

    def get_api_key(self, server_url: str) -> Optional[str]:
        """Retrieve an API key from the credentials store for a specific server URL.

        Args:
            server_url: The server URL for which to retrieve the API key.

        Returns:
            The stored API key if it exists, None otherwise.
        """
        self.check_and_reload_from_file()
        credential = self.credentials.get(server_url)
        if credential:
            return credential.api_key
        return None

    def get_token(
        self, server_url: str, allow_expired: bool = False
    ) -> Optional[APIToken]:
        """Retrieve a valid token from the credentials store for a specific server URL.

        Args:
            server_url: The server URL for which to retrieve the token.
            allow_expired: Whether to allow expired tokens to be returned. The
                default behavior is to return None if a token does exist but is
                expired.

        Returns:
            The stored token if it exists and is not expired, None otherwise.
        """
        self.check_and_reload_from_file()
        credential = self.credentials.get(server_url)
        if credential:
            token = credential.api_token
            if token and (not token.expired or allow_expired):
                return token
        return None

    def get_credentials(self, server_url: str) -> Optional[ServerCredentials]:
        """Retrieve the credentials for a specific server URL.

        Args:
            server_url: The server URL for which to retrieve the credentials.

        Returns:
            The stored credentials if they exist, None otherwise.
        """
        self.check_and_reload_from_file()
        return self.credentials.get(server_url)

    def get_pro_token(self, allow_expired: bool = False) -> Optional[APIToken]:
        """Retrieve a valid token from the credentials store for the ZenML Pro API server.

        Args:
            allow_expired: Whether to allow expired tokens to be returned. The
                default behavior is to return None if a token does exist but is
                expired.

        Returns:
            The stored token if it exists and is not expired, None otherwise.
        """
        return self.get_token(ZENML_PRO_API_URL, allow_expired)

    def get_pro_credentials(
        self, allow_expired: bool = False
    ) -> Optional[ServerCredentials]:
        """Retrieve a valid token from the credentials store for the ZenML Pro API server.

        Args:
            allow_expired: Whether to allow expired tokens to be returned. The
                default behavior is to return None if a token does exist but is
                expired.

        Returns:
            The stored credentials if they exist and are not expired, None otherwise.
        """
        credential = self.get_credentials(ZENML_PRO_API_URL)
        if (
            credential
            and credential.api_token
            and (not credential.api_token.expired or allow_expired)
        ):
            return credential
        return None

    def clear_pro_credentials(self) -> None:
        """Delete the token from the store for the ZenML Pro API server."""
        self.clear_token(ZENML_PRO_API_URL)

    def clear_all_pro_tokens(self) -> None:
        """Delete all tokens from the store for ZenML Pro API servers."""
        for server_url, server in self.credentials.copy().items():
            if server.type == ServerType.PRO:
                if server.api_key:
                    continue
                self.clear_token(server_url)

    def has_valid_authentication(self, url: str) -> bool:
        """Check if a valid authentication credential for the given server URL is stored.

        Args:
            url: The server URL for which to check the authentication.

        Returns:
            bool: True if a valid token or API key is stored, False otherwise.
        """
        credential = self.credentials.get(url)

        if not credential:
            return False
        if credential.api_key or (
            credential.username and credential.password is not None
        ):
            return True
        token = credential.api_token
        return token is not None and not token.expired

    def has_valid_pro_authentication(self) -> bool:
        """Check if a valid token for the ZenML Pro API server is stored.

        Returns:
            bool: True if a valid token is stored, False otherwise.
        """
        return self.get_token(ZENML_PRO_API_URL) is not None

    def set_api_key(
        self,
        server_url: str,
        api_key: str,
    ) -> None:
        """Store an API key in the credentials store for a specific server URL.

        If an API token or a password is already stored for the server URL, they
        will be replaced by the API key.

        Args:
            server_url: The server URL for which the token is to be stored.
            api_key: The API key to store.
        """
        credential = self.credentials.get(server_url)
        if credential and credential.api_key != api_key:
            # Reset the API token if a new or updated API key is set, because
            # the current token might have been issued for a different account
            credential.api_token = None
            credential.api_key = api_key
            credential.username = None
            credential.password = None
        else:
            self.credentials[server_url] = ServerCredentials(
                url=server_url, api_key=api_key
            )

        self._save_credentials()

    def set_password(
        self,
        server_url: str,
        username: str,
        password: str,
    ) -> None:
        """Store a username and password in the credentials store for a specific server URL.

        If an API token is already stored for the server URL, it will be
        replaced by the username and password.

        Args:
            server_url: The server URL for which the token is to be stored.
            username: The username to store.
            password: The password to store.
        """
        credential = self.credentials.get(server_url)
        if credential and (
            credential.username != username or credential.password != password
        ):
            # Reset the API token if a new or updated password is set, because
            # the current token might have been issued for a different account
            credential.api_token = None
            credential.username = username
            credential.password = password
            credential.api_key = None
        else:
            self.credentials[server_url] = ServerCredentials(
                url=server_url, username=username, password=password
            )

        self._save_credentials()

    def set_token(
        self,
        server_url: str,
        token_response: OAuthTokenResponse,
    ) -> APIToken:
        """Store an API token received from an OAuth2 server.

        Args:
            server_url: The server URL for which the token is to be stored.
            token_response: Token response received from an OAuth2 server.

        Returns:
            APIToken: The stored token.
        """
        if token_response.expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_response.expires_in
            )
            # Best practice to calculate the leeway depending on the token
            # expiration time:
            #
            # - for short-lived tokens (less than 1 hour), use a fixed leeway of
            # a few seconds (e.g., 30 seconds)
            # - for longer-lived tokens (e.g., 1 hour or more), use a
            # percentage-based leeway of 5-10%
            if token_response.expires_in < 3600:
                leeway = 30
            else:
                leeway = token_response.expires_in // 20
        else:
            expires_at = None
            leeway = None

        api_token = APIToken(
            access_token=token_response.access_token,
            expires_in=token_response.expires_in,
            expires_at=expires_at,
            leeway=leeway,
            cookie_name=token_response.cookie_name,
            device_id=token_response.device_id,
            device_metadata=token_response.device_metadata,
        )

        credential = self.credentials.get(server_url)
        if credential:
            credential.api_token = api_token
        else:
            self.credentials[server_url] = ServerCredentials(
                url=server_url, api_token=api_token
            )

        self._save_credentials()

        return api_token

    def set_bare_token(
        self,
        server_url: str,
        token: str,
    ) -> APIToken:
        """Store a bare API token.

        Args:
            server_url: The server URL for which the token is to be stored.
            token: The token to store.

        Returns:
            APIToken: The stored token.
        """
        api_token = APIToken(
            access_token=token,
        )

        credential = self.credentials.get(server_url)
        if credential:
            credential.api_token = api_token
        else:
            self.credentials[server_url] = ServerCredentials(
                url=server_url, api_token=api_token
            )

        self._save_credentials()

        return api_token

    def update_server_info(
        self,
        server_url: str,
        server_info: Union[ServerModel, TenantRead],
    ) -> None:
        """Update the server information stored for a specific server URL.

        Args:
            server_url: The server URL for which the server information is to be
                updated.
            server_info: Updated server information.
        """
        credential = self.credentials.get(server_url)
        if not credential:
            # No credentials stored for this server URL, nothing to update
            return

        credential.update_server_info(server_info)
        self._save_credentials()

    def clear_token(self, server_url: str) -> None:
        """Delete a token from the store for a specific server URL.

        Args:
            server_url: The server URL for which to delete the token.
        """
        if server_url in self.credentials:
            credential = self.credentials[server_url]
            if (
                not credential.api_key
                and not credential.username
                and not credential.password is not None
            ):
                # Only delete the credential entry if there is no API key or
                # username/password to fall back on
                del self.credentials[server_url]
            else:
                credential.api_token = None
            self._save_credentials()

    def clear_credentials(self, server_url: str) -> None:
        """Delete all credentials from the store for a specific server URL.

        Args:
            server_url: The server URL for which to delete the credentials.
        """
        if server_url in self.credentials:
            del self.credentials[server_url]
            self._save_credentials()

    def list_credentials(
        self, type: Optional[ServerType] = None
    ) -> List[ServerCredentials]:
        """Get all credentials stored in the credentials store.

        Args:
            type: Optional server type to filter the credentials by.

        Returns:
            A list of all credentials stored in the credentials store.
        """
        credentials = list(self.credentials.values())

        if type is not None:
            credentials = [c for c in credentials if c and c.type == type]

        return credentials


def get_credentials_store() -> CredentialsStore:
    """Get the global credentials store instance.

    Returns:
        The global credentials store instance.
    """
    return CredentialsStore()
