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
"""Functionality to support ZenML GlobalConfiguration."""

import os
from secrets import token_hex
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, SecretStr, root_validator

from zenml.constants import (
    DEFAULT_ZENML_JWT_TOKEN_ALGORITHM,
    DEFAULT_ZENML_JWT_TOKEN_LEEWAY,
    ENV_ZENML_SERVER_PREFIX,
)
from zenml.enums import AuthScheme
from zenml.logger import get_logger
from zenml.models.server_models import ServerDeploymentType

logger = get_logger(__name__)


def generate_jwt_secret_key() -> str:
    """Generate a random JWT secret key.

    This key is used to sign and verify generated JWT tokens.

    Returns:
        A random JWT secret key.
    """
    return token_hex(32)


class ServerConfiguration(BaseModel):
    """ZenML Server configuration attributes.

    Attributes:
        deployment_type: The type of ZenML server deployment that is running.
        root_url_path: The root URL path of the ZenML server.
        auth_scheme: The authentication scheme used by the ZenML server.
        jwt_token_algorithm: The algorithm used to sign and verify JWT tokens.
        jwt_token_issuer: The issuer of the JWT tokens. If not specified, the
            issuer is set to the ZenML Server ID.
        jwt_token_audience: The audience of the JWT tokens. If not specified,
            the audience is set to the ZenML Server ID.
        jwt_token_leeway_seconds: The leeway in seconds allowed when verifying
            the expiration time of JWT tokens.
        jwt_token_expire_minutes: The expiration time of JWT tokens in minutes.
            If not specified, generated JWT tokens will not be set to expire.
        jwt_secret_key: The secret key used to sign and verify JWT tokens. If
            not specified, a random secret key is generated.
        auth_cookie_name: The name of the http-only cookie used to store the JWT
            token. If not specified, the cookie name is set to a value computed
            from the ZenML server ID.
        auth_cookie_domain: The domain of the http-only cookie used to store the
            JWT token. If not specified, the cookie will be valid for the
            domain where the ZenML server is running.
        cors_allow_origins: The origins allowed to make cross-origin requests
            to the ZenML server. If not specified, all origins are allowed.
        external_login_url: The login URL of an external authenticator service
            to use with the `EXTERNAL` authentication scheme.
        external_user_info_url: The user info URL of an external authenticator
            service to use with the `EXTERNAL` authentication scheme.
        external_cookie_name: The name of the http-only cookie used to store the
            bearer token used to authenticate with the external authenticator
            service. Must be specified if the `EXTERNAL` authentication scheme
            is used.
    """

    deployment_type: ServerDeploymentType = ServerDeploymentType.OTHER
    root_url_path: str = ""
    auth_scheme: AuthScheme = AuthScheme.OAUTH2_PASSWORD_BEARER
    jwt_token_algorithm: str = DEFAULT_ZENML_JWT_TOKEN_ALGORITHM
    jwt_token_issuer: Optional[str] = None
    jwt_token_audience: Optional[str] = None
    jwt_token_leeway_seconds: int = DEFAULT_ZENML_JWT_TOKEN_LEEWAY
    jwt_token_expire_minutes: Optional[int] = None
    jwt_secret_key: str = Field(default_factory=generate_jwt_secret_key)
    auth_cookie_name: str
    auth_cookie_domain: Optional[str] = None
    cors_allow_origins: Optional[List[str]] = None

    external_login_url: Optional[str] = None
    external_user_info_url: Optional[str] = None
    external_cookie_name: Optional[str] = None

    @root_validator(pre=True)
    def _validate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the server configuration.

        Args:
            values: The server configuration values.

        Returns:
            The validated server configuration values.

        Raises:
            ValueError: If the server configuration is invalid.
        """
        if values.get("auth_scheme") == AuthScheme.EXTERNAL:
            # If the authentication scheme is set to `EXTERNAL`, the
            # external authenticator URLs must be specified.
            if not values.get("external_login_url") or not values.get(
                "external_user_info_url"
            ):
                raise ValueError(
                    "The external login and user info authenticator "
                    "URLs must be specified when using the EXTERNAL "
                    "authentication scheme."
                )

            # If the authentication scheme is set to `EXTERNAL`, the
            # JWT secret key must be explicitly specified.
            if not values.get("jwt_secret_key"):
                raise ValueError(
                    "The JWT secret key must be explicitly configured "
                    "when using the EXTERNAL authentication scheme."
                )

            # If the authentication scheme is set to `EXTERNAL`, the
            # external cookie name must be specified.
            if not values.get("external_cookie_name"):
                raise ValueError(
                    "The external cookie name must be specified when "
                    "using the EXTERNAL authentication scheme."
                )

        if values.get("auth_scheme") in [
            None,
            AuthScheme.OAUTH2_PASSWORD_BEARER,
            AuthScheme.EXTERNAL,
        ] and not values.get("auth_cookie_name"):
            from zenml.config.global_config import GlobalConfiguration

            server_id = GlobalConfiguration().zen_store.get_deployment_id()

            # If the authentication scheme is set to `OAUTH2_PASSWORD_BEARER`
            # (default) or `EXTERNAL`, an the name of the authentication cookie
            # is not specified, it will be set to a value computed from the
            # ZenML server ID.
            values["auth_cookie_name"] = f"zenml-server-{server_id}"

            # If the issuer or audience is not specified, it is set to the
            # ZenML server ID.
            server_id = GlobalConfiguration().zen_store.get_deployment_id()

            if not values.get("jwt_token_issuer"):
                values["jwt_token_issuer"] = str(server_id)

            if not values.get("jwt_token_audience"):
                values["jwt_token_audience"] = str(server_id)

        if cors_allow_origins := values.get("cors_allow_origins"):
            origins = cors_allow_origins.split(",")
            values["cors_allow_origins"] = origins
        else:
            values["cors_allow_origins"] = ["*"]

        return values

    @classmethod
    def get_server_config(cls) -> "ServerConfiguration":
        """Get the server configuration.

        Returns:
            The server configuration.
        """
        env_server_config: Dict[str, Any] = {}
        for k, v in os.environ.items():
            if v == "":
                continue
            if k.startswith(ENV_ZENML_SERVER_PREFIX):
                env_server_config[
                    k[len(ENV_ZENML_SERVER_PREFIX) :].lower()
                ] = v

        return ServerConfiguration(**env_server_config)

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Allow extra attributes from configs of previous ZenML versions to
        # permit downgrading
        extra = "allow"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True

        # This is needed to allow correct handling of SecretStr values during
        # serialization.
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None
        }
