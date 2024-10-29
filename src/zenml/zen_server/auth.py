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
from datetime import datetime
from typing import Callable, Optional, Union
from urllib.parse import urlencode
from uuid import UUID

import requests
from fastapi import Depends
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    OAuth2PasswordBearer,
)
from pydantic import BaseModel
from starlette.requests import Request

from zenml.analytics.context import AnalyticsContext
from zenml.constants import (
    API,
    DEFAULT_USERNAME,
    EXTERNAL_AUTHENTICATOR_TIMEOUT,
    LOGIN,
    VERSION_1,
)
from zenml.enums import AuthScheme, OAuthDeviceStatus
from zenml.exceptions import (
    AuthorizationException,
    CredentialsNotValid,
    OAuthError,
)
from zenml.logger import get_logger
from zenml.models import (
    APIKey,
    APIKeyInternalResponse,
    APIKeyInternalUpdate,
    ExternalUserModel,
    OAuthDeviceInternalResponse,
    OAuthDeviceInternalUpdate,
    UserAuthModel,
    UserRequest,
    UserResponse,
    UserUpdate,
)
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_server.jwt import JWTToken
from zenml.zen_server.utils import server_config, zen_store

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

    user: UserResponse
    access_token: Optional[JWTToken] = None
    encoded_access_token: Optional[str] = None
    device: Optional[OAuthDeviceInternalResponse] = None
    api_key: Optional[APIKeyInternalResponse] = None


def _fetch_and_verify_api_key(
    api_key_id: UUID, key_to_verify: Optional[str] = None
) -> APIKeyInternalResponse:
    """Fetches an API key from the database and verifies it.

    Args:
        api_key_id: The API key ID.
        key_to_verify: Optional API key value to verify against the API key.

    Returns:
        The fetched API key.

    Raises:
        CredentialsNotValid: If the API key could not be found, is not
            active, if it could not be verified against the supplied key value
            or if the associated service account is not active.
    """
    store = zen_store()

    try:
        api_key = zen_store().get_internal_api_key(api_key_id)
    except KeyError:
        error = (
            f"Authentication error: error retrieving API key " f"{api_key_id}"
        )
        logger.error(error)
        raise CredentialsNotValid(error)

    if not api_key.service_account.active:
        error = (
            f"Authentication error: service account "
            f"{api_key.service_account.name} "
            f"associated with API key {api_key.name} is not active"
        )
        logger.exception(error)
        raise CredentialsNotValid(error)

    if not api_key.active:
        error = (
            f"Authentication error: API key "
            f"{api_key.name} "
            f"associated with service account "
            f"{api_key.service_account.name} is not active"
        )
        logger.error(error)
        raise CredentialsNotValid(error)

    if key_to_verify and not api_key.verify_key(key_to_verify):
        error = (
            f"Authentication error: could not verify key value for API key "
            f"{api_key.name}"
        )
        logger.exception(error)
        raise CredentialsNotValid(error)

    # Update the "last used" timestamp of the API key
    store.update_internal_api_key(
        api_key.id,
        APIKeyInternalUpdate(update_last_login=True),
    )

    return api_key


def authenticate_credentials(
    user_name_or_id: Optional[Union[str, UUID]] = None,
    password: Optional[str] = None,
    access_token: Optional[str] = None,
    activation_token: Optional[str] = None,
) -> AuthContext:
    """Verify if user authentication credentials are valid.

    This function can be used to validate all supplied user credentials to
    cover a range of possibilities:

     * username only - only when the no-auth scheme is used
     * username+password - for basic HTTP authentication or the OAuth2 password
       grant
     * access token (with embedded user id) - after successful authentication
       using one of the supported grants
     * username+activation token - for user activation

    Args:
        user_name_or_id: The username or user ID.
        password: The password.
        access_token: The access token.
        activation_token: The activation token.

    Returns:
        The authenticated account details.

    Raises:
        CredentialsNotValid: If the credentials are invalid.
    """
    user: Optional[UserAuthModel] = None
    auth_context: Optional[AuthContext] = None
    if user_name_or_id:
        try:
            # NOTE: this method will not return a user if the user name or ID
            # identifies a service account instead of a regular user. This
            # is intentional because service accounts are not allowed to
            # be used to authenticate to the API using a username and password,
            # or an activation token.
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
                f"Authentication error: error retrieving account "
                f"{user_name_or_id}"
            )
            pass

    if password is not None:
        if not UserAuthModel.verify_password(password, user):
            error = "Authentication error: invalid username or password"
            logger.error(error)
            raise CredentialsNotValid(error)
        if user and not user.active:
            error = f"Authentication error: user {user.name} is not active"
            logger.error(error)
            raise CredentialsNotValid(error)

    elif activation_token is not None:
        if not UserAuthModel.verify_activation_token(activation_token, user):
            error = (
                f"Authentication error: invalid activation token for user "
                f"{user_name_or_id}"
            )
            logger.error(error)
            raise CredentialsNotValid(error)

    elif access_token is not None:
        try:
            decoded_token = JWTToken.decode_token(
                token=access_token,
            )
        except CredentialsNotValid as e:
            error = f"Authentication error: error decoding access token: {e}."
            logger.exception(error)
            raise CredentialsNotValid(error)

        try:
            user_model = zen_store().get_user(
                user_name_or_id=decoded_token.user_id, include_private=True
            )
        except KeyError:
            error = (
                f"Authentication error: error retrieving token account "
                f"{decoded_token.user_id}"
            )
            logger.error(error)
            raise CredentialsNotValid(error)

        if not user_model.active:
            error = (
                f"Authentication error: account {user_model.name} is not "
                f"active"
            )
            logger.error(error)
            raise CredentialsNotValid(error)

        api_key_model: Optional[APIKeyInternalResponse] = None
        if decoded_token.api_key_id:
            # The API token was generated from an API key. We still have to
            # verify if the API key hasn't been deactivated or deleted in the
            # meantime.
            api_key_model = _fetch_and_verify_api_key(decoded_token.api_key_id)

        device_model: Optional[OAuthDeviceInternalResponse] = None
        if decoded_token.device_id:
            # Access tokens that have been issued for a device are only valid
            # for that device, so we need to check if the device ID matches any
            # of the valid devices in the database.
            try:
                device_model = zen_store().get_internal_authorized_device(
                    device_id=decoded_token.device_id
                )
            except KeyError:
                error = (
                    f"Authentication error: error retrieving token device "
                    f"{decoded_token.device_id}"
                )
                logger.error(error)
                raise CredentialsNotValid(error)

            if (
                device_model.user is None
                or device_model.user.id != user_model.id
            ):
                error = (
                    f"Authentication error: device {decoded_token.device_id} "
                    f"does not belong to user {user_model.name}"
                )
                logger.error(error)
                raise CredentialsNotValid(error)

            if device_model.status != OAuthDeviceStatus.ACTIVE:
                error = (
                    f"Authentication error: device {decoded_token.device_id} "
                    f"is not active"
                )
                logger.error(error)
                raise CredentialsNotValid(error)

            if (
                device_model.expires
                and datetime.utcnow() >= device_model.expires
            ):
                error = (
                    f"Authentication error: device {decoded_token.device_id} "
                    "has expired"
                )
                logger.error(error)
                raise CredentialsNotValid(error)

            zen_store().update_internal_authorized_device(
                device_id=device_model.id,
                update=OAuthDeviceInternalUpdate(
                    update_last_login=True,
                ),
            )

        auth_context = AuthContext(
            user=user_model,
            access_token=decoded_token,
            encoded_access_token=access_token,
            device=device_model,
            api_key=api_key_model,
        )

    else:
        # IMPORTANT: the ONLY way we allow the authentication process to
        # continue without any credentials (i.e. no password, activation
        # token or access token) is if authentication is explicitly disabled
        # by setting the auth_scheme to NO_AUTH.
        if server_config().auth_scheme != AuthScheme.NO_AUTH:
            error = "Authentication error: no credentials provided"
            logger.error(error)
            raise CredentialsNotValid(error)

    if not auth_context:
        error = "Authentication error: invalid credentials"
        logger.error(error)
        raise CredentialsNotValid(error)

    return auth_context


def authenticate_device(client_id: UUID, device_code: str) -> AuthContext:
    """Verify if device authorization credentials are valid.

    Args:
        client_id: The OAuth2 client ID.
        device_code: The device code.

    Returns:
        The authenticated account details.

    Raises:
        OAuthError: If the device authorization credentials are invalid.
    """
    # This is the part of the OAuth2 device code grant flow where a client
    # device is continuously polling the server to check if the user has
    # authorized a device. The following needs to happen to successfully
    # authenticate the device and return a valid access token:
    #
    # 1. the device code and client ID must match a device in the DB
    # 2. the device must be in the VERIFIED state, meaning that the user
    # has successfully authorized the device via the user code but the
    # device client hasn't yet fetched the associated API access token yet.
    # 3. the device must not be expired

    config = server_config()
    store = zen_store()

    try:
        device_model = store.get_internal_authorized_device(
            client_id=client_id
        )
    except KeyError:
        error = (
            f"Authentication error: error retrieving device with client ID "
            f"{client_id}"
        )
        logger.error(error)
        raise OAuthError(
            error="invalid_client",
            error_description=error,
        )

    if device_model.status != OAuthDeviceStatus.VERIFIED:
        error = (
            f"Authentication error: device with client ID {client_id} is "
            f"{device_model.status.value}."
        )
        logger.error(error)
        if device_model.status == OAuthDeviceStatus.PENDING:
            oauth_error = "authorization_pending"
        elif device_model.status == OAuthDeviceStatus.LOCKED:
            oauth_error = "access_denied"
        else:
            oauth_error = "expired_token"
        raise OAuthError(
            error=oauth_error,
            error_description=error,
        )

    if device_model.expires and datetime.utcnow() >= device_model.expires:
        error = (
            f"Authentication error: device for client ID {client_id} has "
            "expired"
        )
        logger.error(error)
        raise OAuthError(
            error="expired_token",
            error_description=error,
        )

    # Check the device code
    if not device_model.verify_device_code(device_code):
        # If the device code is invalid, increment the failed auth attempts
        # counter and lock the device if the maximum number of failed auth
        # attempts has been reached.
        failed_auth_attempts = device_model.failed_auth_attempts + 1
        update = OAuthDeviceInternalUpdate(
            failed_auth_attempts=failed_auth_attempts
        )
        if failed_auth_attempts >= config.max_failed_device_auth_attempts:
            update.locked = True

        store.update_internal_authorized_device(
            device_id=device_model.id,
            update=update,
        )

        if failed_auth_attempts >= config.max_failed_device_auth_attempts:
            error = (
                f"Authentication error: device for client ID {client_id} "
                "has been locked due to too many failed authentication "
                "attempts."
            )
        else:
            error = (
                f"Authentication error: device for client ID {client_id} "
                "has an invalid device code."
            )

        logger.error(error)
        raise OAuthError(
            error="access_denied",
            error_description=error,
        )

    # The device is valid, so we can return the user associated with it.
    # This is the one and only time we return an AuthContext authorized by
    # a device code in order to be exchanged for an access token. Subsequent
    # requests to the API will be authenticated using the access token.
    #
    # Update the device state to ACTIVE and set an expiration date for it
    # past which it can no longer be used for authentication. The expiration
    # date also determines the expiration date of the access token issued
    # for this device.
    expires_in: int = 0
    if config.jwt_token_expire_minutes:
        if device_model.trusted_device:
            expires_in = config.trusted_device_expiration_minutes or 0
        else:
            expires_in = config.device_expiration_minutes or 0

    update = OAuthDeviceInternalUpdate(
        status=OAuthDeviceStatus.ACTIVE,
        expires_in=expires_in * 60,
    )
    device_model = zen_store().update_internal_authorized_device(
        device_id=device_model.id,
        update=update,
    )

    # This can never happen because the VERIFIED state is only set if
    # a user verified and has been associated with the device.
    assert device_model.user is not None

    return AuthContext(user=device_model.user, device=device_model)


def authenticate_external_user(external_access_token: str) -> AuthContext:
    """Implement external authentication.

    Args:
        external_access_token: The access token used to authenticate the user
            to the external authenticator.

    Returns:
        The authentication context reflecting the authenticated user.

    Raises:
        AuthorizationException: If the external user could not be authorized.
    """
    config = server_config()
    store = zen_store()

    assert config.external_user_info_url is not None

    # Use the external access token to extract the user information and
    # permissions

    # Get the user information from the external authenticator
    user_info_url = config.external_user_info_url
    headers = {"Authorization": "Bearer " + external_access_token}
    query_params = dict(server_id=str(config.get_external_server_id()))

    try:
        auth_response = requests.get(
            user_info_url,
            headers=headers,
            params=urlencode(query_params),
            timeout=EXTERNAL_AUTHENTICATOR_TIMEOUT,
        )
    except Exception as e:
        logger.exception(
            f"Error fetching user information from external authenticator: "
            f"{e}"
        )
        raise AuthorizationException(
            "Error fetching user information from external authenticator."
        )

    external_user: Optional[ExternalUserModel] = None

    if 200 <= auth_response.status_code < 300:
        try:
            payload = auth_response.json()
        except requests.exceptions.JSONDecodeError:
            logger.exception(
                "Error decoding JSON response from external authenticator."
            )
            raise AuthorizationException(
                "Unknown external authenticator error"
            )

        if isinstance(payload, dict):
            try:
                external_user = ExternalUserModel.model_validate(payload)
            except Exception as e:
                logger.exception(
                    f"Error parsing user information from external "
                    f"authenticator: {e}"
                )
                pass

    elif auth_response.status_code in [401, 403]:
        raise AuthorizationException("Not authorized to access this server.")
    elif auth_response.status_code == 404:
        raise AuthorizationException(
            "External authenticator did not recognize this server."
        )
    else:
        logger.error(
            f"Error fetching user information from external authenticator. "
            f"Status code: {auth_response.status_code}, "
            f"Response: {auth_response.text}"
        )
        raise AuthorizationException(
            "Error fetching user information from external authenticator. "
        )

    if not external_user:
        raise AuthorizationException("Unknown external authenticator error")

    # With an external user object, we can now authenticate the user against
    # the ZenML server

    # Check if the external user already exists in the ZenML server database
    # If not, create a new user. If yes, update the existing user.
    try:
        user = store.get_external_user(user_id=external_user.id)

        # Update the user information
        user = store.update_user(
            user_id=user.id,
            user_update=UserUpdate(
                name=external_user.email,
                full_name=external_user.name or "",
                email_opted_in=True,
                active=True,
                email=external_user.email,
                is_admin=external_user.is_admin,
            ),
        )
    except KeyError:
        logger.info(
            f"External user with ID {external_user.id} not found in ZenML "
            f"server database. Creating a new user."
        )
        user = store.create_user(
            UserRequest(
                name=external_user.email,
                full_name=external_user.name or "",
                external_user_id=external_user.id,
                email_opted_in=True,
                active=True,
                email=external_user.email,
                is_admin=external_user.is_admin,
            )
        )

        with AnalyticsContext() as context:
            context.user_id = user.id
            context.identify(
                traits={
                    "email": external_user.email,
                    "source": "external_auth",
                }
            )
            context.alias(user_id=external_user.id, previous_id=user.id)

    return AuthContext(user=user)


def authenticate_api_key(
    api_key: str,
) -> AuthContext:
    """Implement service account API key authentication.

    Args:
        api_key: The service account API key.


    Returns:
        The authentication context reflecting the authenticated service account.

    Raises:
        CredentialsNotValid: If the service account could not be authorized.
    """
    try:
        decoded_api_key = APIKey.decode_api_key(api_key)
    except ValueError:
        error = "Authentication error: error decoding API key"
        logger.exception(error)
        raise CredentialsNotValid(error)

    internal_api_key = _fetch_and_verify_api_key(
        api_key_id=decoded_api_key.id, key_to_verify=decoded_api_key.key
    )

    # For now, a lot of code still relies on the active user in the auth
    # context being a UserResponse object, which is a superset of the
    # ServiceAccountResponse object. So we need to convert the service
    # account to a user here.
    user_model = internal_api_key.service_account.to_user_model()
    return AuthContext(user=user_model, api_key=internal_api_key)


def http_authentication(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
) -> AuthContext:
    """Authenticates any request to the ZenML Server with basic HTTP authentication.

    Args:
        credentials: HTTP basic auth credentials passed to the request.

    Returns:
        The authentication context reflecting the authenticated user.

    # noqa: DAR401
    """
    try:
        return authenticate_credentials(
            user_name_or_id=credentials.username, password=credentials.password
        )
    except CredentialsNotValid as e:
        # We want to be very explicit here and return a CredentialsNotValid
        # exception encoded as a 401 Unauthorized error encoded, so that the
        # client can distinguish between a 401 error due to invalid credentials
        # and other 401 errors and handle them accordingly by throwing away the
        # current access token and re-authenticating.
        raise http_exception_from_error(e)


class CookieOAuth2TokenBearer(OAuth2PasswordBearer):
    """OAuth2 token bearer authentication scheme that uses a cookie."""

    async def __call__(self, request: Request) -> Optional[str]:
        """Extract the bearer token from the request.

        Args:
            request: The request.

        Returns:
            The bearer token extracted from the request cookie or header.
        """
        # First, try to get the token from the cookie
        authorization = request.cookies.get(
            server_config().get_auth_cookie_name()
        )
        if authorization:
            logger.info("Got token from cookie")
            return authorization

        # If the token is not present in the cookie, try to get it from the
        # Authorization header
        return await super().__call__(request)


def oauth2_authentication(
    token: str = Depends(
        CookieOAuth2TokenBearer(
            tokenUrl=server_config().root_url_path + API + VERSION_1 + LOGIN,
        )
    ),
) -> AuthContext:
    """Authenticates any request to the ZenML server with OAuth2 JWT tokens.

    Args:
        token: The JWT bearer token to be authenticated.

    Returns:
        The authentication context reflecting the authenticated user.

    # noqa: DAR401
    """
    try:
        auth_context = authenticate_credentials(access_token=token)
    except CredentialsNotValid as e:
        # We want to be very explicit here and return a CredentialsNotValid
        # exception encoded as a 401 Unauthorized error encoded, so that the
        # client can distinguish between a 401 error due to invalid credentials
        # and other 401 errors and handle them accordingly by throwing away the
        # current access token and re-authenticating.
        raise http_exception_from_error(e)

    return auth_context


def no_authentication() -> AuthContext:
    """Doesn't authenticate requests to the ZenML server.

    Returns:
        The authentication context reflecting the default user.
    """
    return authenticate_credentials(user_name_or_id=DEFAULT_USERNAME)


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
