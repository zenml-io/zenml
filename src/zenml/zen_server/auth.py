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

from contextvars import ContextVar
from typing import (
    Callable,
    List,
    Optional,
    Set,
    Union,
)
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    OAuth2PasswordBearer,
    SecurityScopes,
)
from pydantic import BaseModel
from starlette.requests import Request

from zenml.constants import (
    API,
    LOGIN,
    VERSION_1,
)
from zenml.enums import AuthScheme, PermissionType
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import UserResponseModel
from zenml.models.user_models import UserAuthModel
from zenml.zen_server.jwt import JWTToken
from zenml.zen_server.utils import server_config, zen_store
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME

logger = get_logger(__name__)

# create a context variable to store the authentication context
_auth_context: ContextVar[Optional["AuthContext"]] = ContextVar(
    "auth_context", default=None
)


def get_auth_context() -> Optional["AuthContext"]:
    """Returns the current authentication context.

    Returns:
        The authentication context.
    """
    auth_context = _auth_context.get()
    return auth_context


def set_auth_context(auth_context: "AuthContext") -> "AuthContext":
    """Sets the current authentication context.

    Args:
        auth_context: The authentication context.

    Returns:
        The authentication context.
    """
    _auth_context.set(auth_context)
    return auth_context


class AuthContext(BaseModel):
    """The authentication context."""

    user: UserResponseModel
    access_token: Optional[JWTToken] = None

    @property
    def permissions(self) -> Set[PermissionType]:
        """Returns the permissions of the user.

        Returns:
            The permissions of the user.
        """
        if self.user.roles:
            # Merge permissions from all roles
            permissions: List[PermissionType] = []
            for role in self.user.roles:
                permissions.extend(role.permissions)

            # Remove duplicates
            return set(permissions)

        return set()


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
            logger.exception(
                f"Authentication error: error retrieving user "
                f"{user_name_or_id}"
            )
            pass

    if password is not None:
        if not UserAuthModel.verify_password(password, user):
            return None
    elif access_token is not None:
        try:
            decoded_token = JWTToken.decode_token(
                token=access_token,
            )
        except AuthorizationException:
            logger.exception(
                "Authentication error: error decoding access token"
            )
            return None

        try:
            user_model = zen_store().get_user(
                user_name_or_id=decoded_token.user_id, include_private=True
            )
        except KeyError:
            logger.error(
                f"Authentication error: error retrieving user "
                f"{decoded_token.user_id}"
            )
            return None

        if not user_model.active:
            logger.error(
                f"Authentication error: user {decoded_token.user_id} is not "
                f"active"
            )
            return None

        auth_context = AuthContext(user=user_model, access_token=decoded_token)
    elif activation_token is not None:
        if not UserAuthModel.verify_activation_token(activation_token, user):
            logger.error(
                f"Authentication error: invalid activation token for user "
                f"{user_name_or_id}"
            )
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


class CookieOAuth2PasswordBearer(OAuth2PasswordBearer):
    """OAuth2 password bearer authentication scheme that uses a cookie."""

    async def __call__(self, request: Request) -> Optional[str]:
        """Extract the bearer token from the request.

        Args:
            request: The request.

        Returns:
            The bearer token extracted from the request cookie or header.
        """
        # First, try to get the token from the cookie
        authorization = request.cookies.get(server_config().auth_cookie_name)
        if authorization:
            logger.info("Got token from cookie")
            return authorization

        # If the token is not present in the cookie, try to get it from the
        # Authorization header
        return await super().__call__(request)


def oauth2_authentication(
    security_scopes: SecurityScopes,
    token: str = Depends(
        CookieOAuth2PasswordBearer(
            tokenUrl=server_config().root_url_path + API + VERSION_1 + LOGIN,
            scopes={
                "read": "Read permissions on all entities",
                "write": "Write permissions on all entities",
                "me": "Editing permissions to own user",
            },
        )
    ),
) -> AuthContext:
    """Authenticates any request to the ZenML server with OAuth2 JWT tokens.

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

    if auth_context is None or not auth_context.access_token:
        # We have to return an additional WWW-Authenticate header here with the
        # value Bearer to be compliant with the OAuth2 spec.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    for scope in security_scopes.scopes:
        if scope not in auth_context.access_token.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
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
    auth_scheme = server_config().auth_scheme
    if auth_scheme == AuthScheme.NO_AUTH:
        return no_authentication
    elif auth_scheme == AuthScheme.HTTP_BASIC:
        return http_authentication
    elif auth_scheme == AuthScheme.OAUTH2_PASSWORD_BEARER:
        return oauth2_authentication
    elif auth_scheme == AuthScheme.EXTERNAL:
        return oauth2_authentication
    else:
        raise ValueError(f"Unknown authentication scheme: {auth_scheme}")


authorize = authentication_provider()
