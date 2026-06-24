#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""OAuth2 Service Connector."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from pydantic import Field

from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorTypeModel,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)

OAUTH2_CONNECTOR_TYPE = "oauth2"
OAUTH2_API_RESOURCE_TYPE = "oauth2-api"
OAUTH2_SESSION_EXPIRATION_BUFFER = 15  # 15 minutes


class OAuth2AuthenticationMethods(StrEnum):
    """OAuth2 authentication methods."""

    CLIENT_CREDENTIALS = "client-credentials"
    REFRESH_TOKEN = "refresh-token"
    TOKEN = "token"


class OAuth2BaseConfig(AuthenticationConfig):
    """OAuth2 base configuration."""

    api_url: str = Field(title="API base URL")


class OAuth2TokenConfig(OAuth2BaseConfig):
    """OAuth2 token configuration."""

    access_token: PlainSerializedSecretStr = Field(title="OAuth2 access token")


class OAuth2GrantConfig(OAuth2BaseConfig):
    """OAuth2 base configuration for grants that mint access tokens."""

    token_url: str = Field(title="OAuth2 token endpoint URL")
    client_id: str = Field(title="OAuth2 client ID")
    scope: Optional[str] = Field(
        default=None,
        title="Space-separated OAuth2 scopes",
    )


class OAuth2ClientCredentialsConfig(OAuth2GrantConfig):
    """OAuth2 client credentials configuration."""

    client_secret: PlainSerializedSecretStr = Field(
        title="OAuth2 client secret",
    )
    audience: Optional[str] = Field(default=None, title="OAuth2 audience")


class OAuth2RefreshTokenConfig(OAuth2GrantConfig):
    """OAuth2 refresh token configuration."""

    refresh_token: PlainSerializedSecretStr = Field(
        title="OAuth2 refresh token",
    )
    client_secret: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="OAuth2 client secret",
    )


OAUTH2_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="OAuth2 Service Connector",
    connector_type=OAUTH2_CONNECTOR_TYPE,
    description="""
The ZenML OAuth2 Service Connector authenticates to an HTTP API using OAuth2.

The client credentials and refresh token methods exchange long-lived
credentials for a temporary access token at a token endpoint. Connector
consumers only ever receive the temporary token, never the underlying
credentials. A pre-obtained access token can also be supplied directly.

Connecting returns an authenticated requests Session with the bearer token set
on the Authorization header.
""",
    emoji=":closed_lock_with_key:",
    auth_methods=[
        AuthenticationMethodModel(
            name="OAuth2 Client Credentials",
            auth_method=OAuth2AuthenticationMethods.CLIENT_CREDENTIALS,
            description="""
Exchange a client ID and secret for a temporary access token using the OAuth2
client credentials grant.
""",
            config_class=OAuth2ClientCredentialsConfig,
        ),
        AuthenticationMethodModel(
            name="OAuth2 Refresh Token",
            auth_method=OAuth2AuthenticationMethods.REFRESH_TOKEN,
            description="""
Exchange a refresh token for a temporary access token using the OAuth2 refresh
token grant. Rotating refresh tokens are not supported.
""",
            config_class=OAuth2RefreshTokenConfig,
        ),
        AuthenticationMethodModel(
            name="OAuth2 Token",
            auth_method=OAuth2AuthenticationMethods.TOKEN,
            description="""
Use a pre-obtained OAuth2 access token to authenticate with the API.
""",
            config_class=OAuth2TokenConfig,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="OAuth2 API",
            resource_type=OAUTH2_API_RESOURCE_TYPE,
            description="""
Allows access to an HTTP API protected by OAuth2. When used by connector
consumers, the connector provides an authenticated requests Session with the
bearer token set on the Authorization header.
""",
            auth_methods=OAuth2AuthenticationMethods.values(),
            supports_instances=False,
            emoji=":globe_with_meridians:",
        ),
    ],
)


class OAuth2ServiceConnector(ServiceConnector):
    """OAuth2 service connector."""

    config: OAuth2BaseConfig

    _token_cache: Dict[str, Tuple[str, Optional[datetime]]] = {}

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector specification.

        Returns:
            The service connector specification.
        """
        return OAUTH2_SERVICE_CONNECTOR_TYPE_SPEC

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Args:
            resource_type: The type of the resource to get a default resource ID
                for. Only called with resource types that do not support
                multiple instances.

        Returns:
            The default resource ID for the resource type.
        """
        return self.config.api_url

    def _fetch_token(self) -> Tuple[str, Optional[datetime]]:
        """Fetch an access token from the token endpoint.

        Raises:
            AuthorizationException: If a token could not be fetched.

        Returns:
            The access token and its expiration timestamp, if known.
        """
        cfg = self.config
        assert isinstance(cfg, OAuth2GrantConfig)

        data: Dict[str, str] = {}
        auth: Optional[Tuple[str, str]] = None

        if isinstance(cfg, OAuth2ClientCredentialsConfig):
            data["grant_type"] = "client_credentials"
            if cfg.audience:
                data["audience"] = cfg.audience
            auth = (cfg.client_id, cfg.client_secret.get_secret_value())
        elif isinstance(cfg, OAuth2RefreshTokenConfig):
            data["grant_type"] = "refresh_token"
            data["refresh_token"] = cfg.refresh_token.get_secret_value()
            if cfg.client_secret is not None:
                auth = (cfg.client_id, cfg.client_secret.get_secret_value())
            else:
                # Public clients without a secret send the client ID in the
                # request body.
                data["client_id"] = cfg.client_id

        if cfg.scope:
            data["scope"] = cfg.scope

        try:
            response = requests.post(
                cfg.token_url,
                data=data,
                auth=auth,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            token = payload["access_token"]
        except (requests.RequestException, KeyError, ValueError) as e:
            raise AuthorizationException(
                f"Failed to fetch an OAuth2 token from {cfg.token_url}: {e}"
            ) from e

        if not isinstance(token, str):
            raise AuthorizationException(
                f"The OAuth2 token endpoint at {cfg.token_url} returned an "
                f"invalid access token."
            )

        expires_at: Optional[datetime] = None
        expires_in = payload.get("expires_in")
        if expires_in is not None:
            expires_at = utc_now(tz_aware=True) + timedelta(
                seconds=int(expires_in)
            )

        return token, expires_at

    def _get_token(self) -> Tuple[str, Optional[datetime]]:
        """Get the access token and its expiration timestamp, if known.

        Returns:
            The access token and its expiration timestamp, if known.
        """
        if isinstance(self.config, OAuth2TokenConfig):
            # Use the user-configured expires_at timestamp on the connector
            # configuration for static tokens.
            return self.config.access_token.get_secret_value(), self.expires_at

        key = self.auth_method
        if key in self._token_cache:
            token, expires_at = self._token_cache[key]
            if expires_at is None:
                return token, None

            # Reuse the cached token unless it expires in the near future.
            if expires_at > utc_now(tz_aware=expires_at) + timedelta(
                minutes=OAUTH2_SESSION_EXPIRATION_BUFFER
            ):
                return token, expires_at

        token, expires_at = self._fetch_token()
        self._token_cache[key] = (token, expires_at)
        return token, expires_at

    def _get_connector_client(
        self,
        resource_type: str,
        resource_id: str,
    ) -> "ServiceConnector":
        """Get a connector client scoped to a temporary access token.

        Args:
            resource_type: The type of the resource to connect to.
            resource_id: The ID of the resource to connect to.

        Returns:
            A service connector client that can be used to connect to the
            resource.
        """
        token, expires_at = self._get_token()

        return OAuth2ServiceConnector(
            auth_method=OAuth2AuthenticationMethods.TOKEN,
            resource_type=resource_type,
            resource_id=resource_id,
            config=OAuth2TokenConfig(
                access_token=token,
                api_url=self.config.api_url,
            ),
            expires_at=expires_at,
            expires_skew_tolerance=self.expires_skew_tolerance,
        )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and return a requests session for the API.

        Args:
            kwargs: Additional implementation specific keyword arguments.

        Returns:
            An authenticated requests Session.
        """
        token, _ = self._get_token()

        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token}"
        return session

    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to connect to the API.

        Args:
            kwargs: Additional implementation specific keyword arguments.

        Raises:
            NotImplementedError: Always, since there is no local client to
                configure.
        """
        raise NotImplementedError(
            "Local client configuration is not supported by the OAuth2 "
            "connector."
        )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "OAuth2ServiceConnector":
        """Auto-configure the connector.

        Args:
            auth_method: The authentication method to use.
            resource_type: The type of resource to configure.
            resource_id: The ID of the resource to configure.
            kwargs: Additional implementation specific keyword arguments.

        Raises:
            NotImplementedError: Always, since auto-configuration is not
                supported.

        Returns:
            The auto-configured connector.
        """
        raise NotImplementedError(
            "Auto-configuration is not supported by the OAuth2 connector."
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify that the connector can authenticate and access the API.

        Args:
            resource_type: The type of resource to verify.
            resource_id: The ID of the resource to verify.

        Returns:
            The list of resource IDs that the connector can access.
        """
        # We can only verify grant-based methods by fetching a token. A static
        # token cannot be verified without calling the API.
        if isinstance(self.config, OAuth2GrantConfig):
            self._get_token()
        return [resource_id] if resource_id else []
