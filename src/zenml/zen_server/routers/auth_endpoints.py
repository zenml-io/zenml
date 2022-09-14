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
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.param_functions import Form
from fastapi.security import OAuth2PasswordRequestForm

from zenml.constants import LOGIN, LOGOUT, VERSION_1
from zenml.zen_server.auth import (
    authenticate_user,
)
from zenml.zen_server.utils import (
    error_response,
)

router = APIRouter(
    prefix=VERSION_1,
    tags=["auth"],
    responses={401: error_response},
)


class PasswordRequestForm:
    """OAuth2 password grant type request form.

    This form is similar to fastapi.security.OAuth2PasswordRequestForm, with
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
async def token(auth_form_data: PasswordRequestForm = Depends()):
    auth_context = authenticate_user(
        auth_form_data.username, auth_form_data.password
    )
    if not auth_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_context.user.generate_access_token()

    # The response of the token endpoint must be a JSON object with the
    # following fields:
    #
    #   * token_type - the token type (must be "bearer" in our case)
    #   * access_token - string containing the access token
    return {"access_token": access_token, "token_type": "bearer"}
