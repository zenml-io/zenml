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
"""Endpoint definitions for authentication (login)."""

from typing import Optional
from urllib.parse import urlencode
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.param_functions import Form
from pydantic import BaseModel
from starlette.requests import Request

from zenml.constants import API, AUTHORIZE, LOGIN, VERSION_1
from zenml.enums import AuthScheme
from zenml.logger import get_logger
from zenml.models import UserRoleAssignmentFilterModel
from zenml.models.user_models import UserRequestModel, UserUpdateModel
from zenml.models.user_role_assignment_models import (
    UserRoleAssignmentRequestModel,
)
from zenml.zen_server.auth import authenticate_credentials
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.jwt import JWTToken
from zenml.zen_server.utils import server_config, zen_store

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["auth"],
    responses={401: error_response},
)


class PasswordRequestForm:
    """OAuth2 password grant type request form.

    This form is similar to `fastapi.security.OAuth2PasswordRequestForm`, with
    the single difference being that it also allows an empty password.
    """

    def __init__(
        self,
        grant_type: str = Form(None, regex="password"),
        username: str = Form(...),
        password: Optional[str] = Form(""),
        scope: str = Form(""),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
    ):
        """Initializes the form.

        Args:
            grant_type: The grant type.
            username: The username.
            password: The password.
            scope: The scope.
            client_id: The client ID.
            client_secret: The client secret.
        """
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.scope = scope
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


class AuthenticationResponse(BaseModel):
    """Authentication response."""

    authorization_url: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None


if server_config().auth_scheme == AuthScheme.OAUTH2_PASSWORD_BEARER:

    @router.post(
        LOGIN,
        responses={401: error_response},
        response_model=AuthenticationResponse,
    )
    def token(
        response: Response,
        auth_form_data: PasswordRequestForm = Depends(),
    ) -> AuthenticationResponse:
        """Returns an access token for the given user.

        Args:
            response: The response object.
            auth_form_data: The authentication form data.

        Returns:
            An access token.

        Raises:
            HTTPException: 401 if not authorized to login.
        """
        auth_context = authenticate_credentials(
            user_name_or_id=auth_form_data.username,
            password=auth_form_data.password,
        )
        if not auth_context:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        role_assignments = zen_store().list_user_role_assignments(
            user_role_assignment_filter_model=UserRoleAssignmentFilterModel(
                user_id=auth_context.user.id
            )
        )

        # TODO: This needs to happen at the sql level now
        permissions = set().union(
            *[
                zen_store().get_role(ra.role.id).permissions
                for ra in role_assignments.items
                if ra.role is not None
            ]
        )

        access_token = JWTToken(
            user_id=auth_context.user.id,
            permissions=[p.value for p in permissions],
        ).encode()

        config = server_config()

        # Also set the access token as an HTTP only cookie in the response
        response.set_cookie(
            key=config.auth_cookie_name,
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=config.jwt_token_expire_minutes * 60
            if config.jwt_token_expire_minutes
            else None,
            domain=config.auth_cookie_domain,
        )

        # The response of the token endpoint must be a JSON object with the
        # following fields:
        #
        #   * token_type - the token type (must be "bearer" in our case)
        #   * access_token - string containing the access token
        return AuthenticationResponse(
            access_token=access_token, token_type="bearer"
        )


if server_config().auth_scheme == AuthScheme.EXTERNAL:

    class ExternalUser(BaseModel):
        """External user model."""

        id: UUID
        email: str
        oauth_provider: str
        oauth_id: str
        name: Optional[str] = None
        avatar_url: Optional[str] = None
        company: Optional[str] = None
        job_title: Optional[str] = None

        class Config:
            """Pydantic configuration."""

            # ignore arbitrary fields
            extra = "ignore"

    @router.get(
        AUTHORIZE,
        response_model=AuthenticationResponse,
    )
    def authorize(
        request: Request,
        response: Response,
        redirect_url: Optional[str] = None,
    ) -> AuthenticationResponse:
        """Authorize a user through the external authenticator service.

        Args:
            request: The request object.
            response: The response object.
            redirect_url: The URL to redirect to after successful login.

        Returns:
            An authentication response with an access token or an external
            authorization URL.
        """
        config = server_config()
        store = zen_store()
        assert config.external_cookie_name is not None
        assert config.external_login_url is not None
        assert config.external_user_info_url is not None

        authorization_url = config.external_login_url
        query_params = dict()
        if redirect_url:
            # If a redirect URL is specified, add it to the query params
            # formatted as a URL-encoded string
            query_params["redirect_url"] = redirect_url

        if query_params:
            authorization_url += f"/?{urlencode(query_params)}"

        # Try to get the external access token from the external cookie
        external_access_token = request.cookies.get(
            config.external_cookie_name
        )
        if not external_access_token:
            logger.info(
                "External access token not found in cookie. Redirecting to "
                "external authenticator."
            )

            # Redirect the user to the external authentication login endpoint
            return AuthenticationResponse(authorization_url=authorization_url)

        # If an external access token was found in the cookie, use it to
        # extract the user information and permissions
        logger.info("External access token found in cookie.")

        # Get the user information from the external authenticator
        user_info_url = config.external_user_info_url
        headers = {"Authorization": "Bearer " + external_access_token}
        query_params = dict(server_id=str(zen_store().get_deployment_id()))

        try:
            auth_response = requests.get(
                user_info_url,
                headers=headers,
                params=urlencode(query_params),
            )
        except Exception as e:
            logger.exception(
                f"Error fetching user information from external authenticator: "
                f"{e}"
            )

            # Redirect the user to the external authentication login endpoint
            return AuthenticationResponse(authorization_url=authorization_url)

        external_user: Optional[ExternalUser] = None

        if 200 <= auth_response.status_code < 300:
            try:
                payload = auth_response.json()
            except requests.exceptions.JSONDecodeError:
                logger.exception(
                    "Error decoding JSON response from external authenticator."
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unknown external authenticator error.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if isinstance(payload, dict):
                try:
                    external_user = ExternalUser.parse_obj(payload)
                except Exception as e:
                    logger.exception(
                        f"Error parsing user information from external "
                        f"authenticator: {e}"
                    )
                    pass

        elif auth_response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized to access this server.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            logger.error(
                f"Error fetching user information from external authenticator. "
                f"Status code: {auth_response.status_code}, "
                f"Response: {auth_response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown external authenticator error.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not external_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown external authenticator error.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # With an external user object, we can now authenticate the user against
        # the ZenML server

        # Check if the external user already exists in the ZenML server database
        # If not, create a new user. If yes, update the existing user.
        try:
            user = store.get_external_user(user_id=external_user.id)

            # Update the user information
            user = store.update_user(
                user_id=user.id,
                user_update=UserUpdateModel(
                    name=external_user.name or external_user.email,
                    full_name=external_user.name or "",
                    email_opted_in=True,
                    active=True,
                    email=external_user.email,
                ),
            )
        except KeyError:
            logger.info(
                f"External user with ID {external_user.id} not found in ZenML "
                f"server database. Creating a new user."
            )
            user = store.create_user(
                UserRequestModel(
                    name=external_user.name or external_user.email,
                    full_name=external_user.name or "",
                    external_user_id=external_user.id,
                    email_opted_in=True,
                    active=True,
                    email=external_user.email,
                )
            )

            # Create a new user role assignment for the new user
            store.create_user_role_assignment(
                UserRoleAssignmentRequestModel(
                    role=store._admin_role.id,
                    user=user.id,
                    workspace=None,
                )
            )

        role_assignments = store.list_user_role_assignments(
            user_role_assignment_filter_model=UserRoleAssignmentFilterModel(
                user_id=user.id
            )
        )

        # TODO: This needs to happen at the sql level now
        permissions = set().union(
            *[
                zen_store().get_role(ra.role.id).permissions
                for ra in role_assignments.items
                if ra.role is not None
            ]
        )

        access_token = JWTToken(
            user_id=user.id,
            permissions=[p.value for p in permissions],
        ).encode()

        config = server_config()

        # Also set the access token as an HTTP only cookie in the response
        response.set_cookie(
            key=config.auth_cookie_name,
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=config.jwt_token_expire_minutes * 60
            if config.jwt_token_expire_minutes
            else None,
            domain=config.auth_cookie_domain,
        )

        # The response of the token endpoint must be a JSON object with the
        # following fields:
        #
        #   * token_type - the token type (must be "bearer" in our case)
        #   * access_token - string containing the access token
        return AuthenticationResponse(
            access_token=access_token, token_type="bearer"
        )
