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

from zenml.constants import LOGIN, VERSION_1
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models.user_management_models import (
    JWTToken,
    JWTTokenType,
    UserModel,
)
from zenml.utils.enum_utils import StrEnum
from zenml.zen_server.utils import zen_store
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME

logger = get_logger(__name__)

JWT_SECRET_KEY = os.environ.get(
    "ZENML_JWT_SECRET_KEY",
    "d38d1a44ae024c21534021d4b208323a8af0f844360a2dc96322056aeab286ff",
)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

ENV_ZENML_AUTH_TYPE = "ZENML_AUTH_TYPE"


class AuthScheme(StrEnum):
    """The authentication scheme."""

    NO_AUTH = "NoAuth"
    HTTP_BASIC = "HTTPBasic"
    OAUTH2_PASSWORD_BEARER = "OAuth2PasswordBearer"


class AuthContext(BaseModel):
    user: UserModel


def authentication_scheme() -> AuthScheme:
    """Returns the authentication type."""
    auth_scheme = AuthScheme(
        os.environ.get(ENV_ZENML_AUTH_TYPE, AuthScheme.OAUTH2_PASSWORD_BEARER)
    )
    return auth_scheme


def validate_user(user_name_or_id: Union[str, UUID]) -> Optional[AuthContext]:
    """Verify if a username is valid.

    Args:
        user_name_or_id: The username or user ID.

    Returns:
        The authenticated account details, if the username is valid, otherwise
        None.
    """
    try:
        user = zen_store.get_user(user_name_or_id)
    except KeyError:
        return None

    return AuthContext(user=user)


def authenticate_user(
    user_name_or_id: str,
    password: str,
) -> Optional[AuthContext]:
    """Verify if authentication credentials are valid.

    Args:
        user_name_or_id: The username or user ID.
        password: The password.

    Returns:
        The authenticated account details, if the account is valid, otherwise
        None.
    """
    try:
        user = zen_store.get_user(user_name_or_id)
    except KeyError:
        return None
    if not user.verify_password(password):
        return None

    return AuthContext(user=user)


def http_authentication(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
) -> None:
    """Authenticates any request to the ZenServer with basic HTTP authentication.

    Args:
        credentials: HTTP basic auth credentials passed to the request.

    Raises:
        HTTPException: If the user credentials could not be authenticated.
    """
    auth_context = authenticate_user(credentials.username, credentials.password)
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def oauth2_password_bearer_authentication(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl=VERSION_1 + LOGIN)),
) -> AuthContext:
    """Authenticates any request to the ZenML server with OAuth2 password bearer JWT tokens.

    Args:
        token: The JWT bearer token to be authenticated.

    Returns:
        The authentication context reflecting the authenticated user.

    Raises:
        HTTPException: If the JWT token could not be authorized.
    """
    # We have to return an additional WWW-Authenticate header here with the
    # value Bearer to be compliant with the OAuth2 spec.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = JWTToken.decode(
            token_type=JWTTokenType.ACCESS_TOKEN, token=token
        )
    except AuthorizationException:
        logger.exception("JWT authorization exception")
        raise credentials_exception

    auth_context = validate_user(token.user_id)
    if auth_context is None:
        logger.error("JWT authorization exception")
        raise credentials_exception

    try:
        auth_context.user.verify_access_token(token)
    except AuthorizationException:
        logger.exception("Could not verify JWT access token")
        raise credentials_exception

    return auth_context


def no_authentication() -> AuthContext:
    """Doesn't authenticate requests to the ZenML server.

    Raises:
        HTTPException: If the default user is not available.
    """
    auth_context = validate_user(DEFAULT_USERNAME)

    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


def authentication_provider() -> Callable[[], AuthContext]:
    """Returns the authentication provider."""
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
