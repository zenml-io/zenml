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
)
from pydantic import BaseModel

from zenml.constants import API, ENV_ZENML_AUTH_TYPE, LOGIN, VERSION_1
from zenml.logger import get_logger
from zenml.models.user_management_models import UserModel
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

    user: UserModel


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

    This function can be used to validate all of the supplied
    user credentials to cover a range of possibilities:

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
    user: Optional[UserModel] = None
    auth_context: Optional[AuthContext] = None
    if user_name_or_id:
        try:
            user = zen_store().get_user(user_name_or_id)
            auth_context = AuthContext(user=user)
        except KeyError:
            # even when the user does not exist, we still want to execute the
            # password/token verification to protect against response discrepancy
            # attacks (https://cwe.mitre.org/data/definitions/204.html)
            pass
    if password is not None:
        if not UserModel.verify_password(password, user):
            return None
    elif access_token is not None:
        user = UserModel.verify_access_token(access_token)
        if not user:
            return None
        auth_context = AuthContext(user=user)
    elif activation_token is not None:
        if not UserModel.verify_activation_token(activation_token, user):
            return None
    return auth_context


def http_authentication(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
) -> AuthContext:
    """Authenticates any request to the ZenML Server with basic HTTP authentication.

    Args:
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
    token: str = Depends(
        OAuth2PasswordBearer(tokenUrl=ROOT_URL_PATH + API + VERSION_1 + LOGIN)
    ),
) -> AuthContext:
    """Authenticates any request to the ZenML server with OAuth2 password bearer JWT tokens.

    Args:
        token: The JWT bearer token to be authenticated.

    Returns:
        The authentication context reflecting the authenticated user.

    Raises:
        HTTPException: If the JWT token could not be authorized.
    """
    auth_context = authenticate_credentials(access_token=token)
    if auth_context is None:
        # We have to return an additional WWW-Authenticate header here with the
        # value Bearer to be compliant with the OAuth2 spec.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_context


def no_authentication() -> AuthContext:
    """Doesn't authenticate requests to the ZenML server.

    Raises:
        HTTPException: If the default user is not available.

    Returns:
        The authentication context reflecting the default user.
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
