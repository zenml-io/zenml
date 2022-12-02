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

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.param_functions import Form

from zenml.constants import API, LOGIN, VERSION_1
from zenml.zen_server.auth import authenticate_credentials
from zenml.zen_server.utils import error_response, zen_store

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


@router.post(
    LOGIN,
    responses={401: error_response},
)
def token(
    auth_form_data: PasswordRequestForm = Depends(),
) -> Dict[str, str]:
    """Returns an access token for the given user.

    Args:
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
    role_assignments = zen_store().list_role_assignments(
        user_name_or_id=auth_context.user.id, project_name_or_id=None
    )

    permissions = set().union(
        *[
            zen_store().get_role(ra.role.id).permissions
            for ra in role_assignments
        ]
    )

    access_token = auth_context.user.generate_access_token(
        permissions=[p.value for p in permissions]
    )
    # The response of the token endpoint must be a JSON object with the
    # following fields:
    #
    #   * token_type - the token type (must be "bearer" in our case)
    #   * access_token - string containing the access token
    return {"access_token": access_token, "token_type": "bearer"}
