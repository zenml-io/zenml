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
"""Authentication module for ZenML server."""

import os
from typing import Callable, Optional, Union
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    OAuth2PasswordBearer,
    SecurityScopes,
)
from pydantic import BaseModel

from zenml.constants import API, ENV_ZENML_AUTH_TYPE, LOGIN, VERSION_1
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import UserResponseModel
from zenml.models.user_models import JWTToken, JWTTokenType, UserAuthModel
from zenml.utils.enum_utils import StrEnum
from zenml.zen_server.utils import ROOT_URL_PATH, zen_store
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME

logger = get_logger(__name__)


class AuthScheme(StrEnum):
    """The authentication scheme."""

    NO_AUTH = "NO_AUTH"
    HTTP_BASIC = "HTTP_BASIC"
    OAUTH2_PASSWORD_BEARER = "OAUTH2_PASSWORD_BEARER"


class AuthContext(BaseModel):
    """The authentication context."""

    user: UserResponseModel


def authentication_scheme() -> AuthScheme:
    """Returns the authentication type.

    Returns:
        The authentication type.
    """
    auth_scheme = AuthScheme(
        os.environ.get(ENV_ZENML_AUTH_TYPE, AuthScheme.OAUTH2_PASSWORD_BEARER)
    )
    return auth_scheme


def authenticate_credentials(
    user_name_or_id: Optional[Union[str, UUID]] = None,
    password: Optional[str] = None,
    access_token: Optional[str] = None,
    activation_token: Optional[str] = None,
) -> Optional[AuthContext]:
    """Verify if user authentication credentials are valid.

    This function can be used to validate all supplied user credentials to
    cover a range of possibilities:

     * username+password
     * access token (with embedded user id)
     * username+activation token

    Args:
        user_name_or_id: The username or user ID.
        password: The password.
        access_token: The access token.
        activation_token: The activation token.

    Returns:
        The authenticated account details, if the account is valid, otherwise
        None.
    """
    user: Optional[UserAuthModel] = None
    auth_context: Optional[AuthContext] = None
    if user_name_or_id:
        try:
            user = zen_store().get_auth_user(user_name_or_id)
            user_model = zen_store().get_user(
                user_name_or_id=user_name_or_id, include_private=True
            )
            auth_context = AuthContext(user=user_model)
        except KeyError:
            # even when the user does not exist, we still want to execute the
            # password/token verification to protect against response discrepancy
            # attacks (https://cwe.mitre.org/data/definitions/204.html)
            pass
    if password is not None:
        if not UserAuthModel.verify_password(password, user):
            return None
    elif access_token is not None:
        user = UserAuthModel.verify_access_token(access_token)
        if not user:
            return None
        user_model = zen_store().get_user(
            user_name_or_id=user.id, include_private=True
        )
        auth_context = AuthContext(user=user_model)
    elif activation_token is not None:
        if not UserAuthModel.verify_activation_token(activation_token, user):
            return None

    return auth_context


def http_authentication(
    security_scopes: SecurityScopes,
    credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
) -> AuthContext:
    """Authenticates any request to the ZenML Server with basic HTTP authentication.

    Args:
        security_scopes: Security scope will be ignored for http_auth
        credentials: HTTP basic auth credentials passed to the request.

    Returns:
        The authentication context reflecting the authenticated user.

    Raises:
        HTTPException: If the user credentials could not be authenticated.
    """
    auth_context = authenticate_credentials(
        user_name_or_id=credentials.username, password=credentials.password
    )
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return auth_context


def oauth2_password_bearer_authentication(
    security_scopes: SecurityScopes,
    token: str = Depends(
        OAuth2PasswordBearer(
            tokenUrl=ROOT_URL_PATH + API + VERSION_1 + LOGIN,
            scopes={
                "read": "Read permissions on all entities",
                "write": "Write permissions on all entities",
                "me": "Editing permissions to own user",
            },
        )
    ),
) -> AuthContext:
    """Authenticates any request to the ZenML server with OAuth2 password bearer JWT tokens.

    Args:
        security_scopes: Security scope for this token
        token: The JWT bearer token to be authenticated.

    Returns:
        The authentication context reflecting the authenticated user.

    Raises:
        HTTPException: If the JWT token could not be authorized.
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    auth_context = authenticate_credentials(access_token=token)

    try:
        access_token = JWTToken.decode(
            token_type=JWTTokenType.ACCESS_TOKEN, token=token
        )
    except AuthorizationException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    for scope in security_scopes.scopes:
        if scope not in access_token.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    if auth_context is None:
        # We have to return an additional WWW-Authenticate header here with the
        # value Bearer to be compliant with the OAuth2 spec.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_context


def no_authentication(security_scopes: SecurityScopes) -> AuthContext:
    """Doesn't authenticate requests to the ZenML server.

    Args:
        security_scopes: Security scope will be ignored for http_auth

    Returns:
        The authentication context reflecting the default user.

    Raises:
        HTTPException: If the default user is not available.
    """
    auth_context = authenticate_credentials(user_name_or_id=DEFAULT_USERNAME)

    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return auth_context


def authentication_provider() -> Callable[..., AuthContext]:
    """Returns the authentication provider.

    Returns:
        The authentication provider.

    Raises:
        ValueError: If the authentication scheme is not supported.
    """
    auth_scheme = authentication_scheme()
    if auth_scheme == AuthScheme.NO_AUTH:
        return no_authentication
    elif auth_scheme == AuthScheme.HTTP_BASIC:
        return http_authentication
    elif auth_scheme == AuthScheme.OAUTH2_PASSWORD_BEARER:
        return oauth2_password_bearer_authentication
    else:
        raise ValueError(f"Unknown authentication scheme: {auth_scheme}")


authorize = authentication_provider()
