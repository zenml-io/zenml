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
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from zenml.constants import LOGIN, LOGOUT, VERSION_1
from zenml.zen_server.auth import authenticate_user, create_access_token
from zenml.zen_server.utils import (
    error_response,
)

router = APIRouter(
    prefix=VERSION_1,
    tags=["auth"],
    responses={401: error_response},
)


@router.post(
    LOGIN,
    responses={401: error_response},
)
async def token(auth_form_data: OAuth2PasswordRequestForm = Depends()):
    auth_context = authenticate_user(
        auth_form_data.username, auth_form_data.password
    )
    if not auth_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(auth_context)

    # The response of the token endpoint must be a JSON object with the
    # following fields:
    #
    #   * token_type - the token type (must be "bearer" in our case)
    #   * access_token - string containing the access token
    return {"access_token": access_token, "token_type": "bearer"}
