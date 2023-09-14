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

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.param_functions import Form

from zenml.constants import API, LOGIN, VERSION_1
from zenml.enums import AuthScheme
from zenml.models import UserRoleAssignmentFilterModel
from zenml.zen_server.auth import authenticate_credentials
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.jwt import JWTToken, get_token_authenticator
from zenml.zen_server.utils import server_config, zen_store

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


if server_config().auth_scheme == AuthScheme.OAUTH2_PASSWORD_BEARER:

    @router.post(
        LOGIN,
        responses={401: error_response},
    )
    def token(
        response: Response,
        auth_form_data: PasswordRequestForm = Depends(),
    ) -> Dict[str, str]:
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

        access_token = get_token_authenticator().encode(
            JWTToken(
                user_id=auth_context.user.id,
                permissions=[p.value for p in permissions],
            )
        )

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
        return {"access_token": access_token, "token_type": "bearer"}

elif server_config().auth_scheme == AuthScheme.EXTERNAL:

    @router.get(
        LOGIN,
        responses={302: {"description": "Redirects to the external login."}},
    )
    def external_login(
        response: Response,
        redirect_url: Optional[str] = None,
    ) -> None:
        """Redirect the user to the external authentication login endpoint.

        Args:
            response: The response object.
            redirect_url: The URL to redirect to after login.
        """
        config = server_config()

        assert config.external_authenticator_url is not None

        # Redirect the user to the external authentication login endpoint
        response.headers["Location"] = (
            config.external_authenticator_url + LOGIN
        )
        if redirect_url:
            response.headers["Location"] += f"?callback_url={redirect_url}"
        response.status_code = status.HTTP_302_FOUND
