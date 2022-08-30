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
from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import LOGIN, LOGOUT, VERSION_1
from zenml.zen_server.utils import (
    authorize,
    conflict,
    error_detail,
    error_response,
    not_found,
    zen_store,
)

router = APIRouter(
    prefix=VERSION_1,
    tags=["auth"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.post(
    LOGIN,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def login() -> None:
    """Login as a user.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        zen_store.login()
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    LOGOUT,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def logout() -> None:
    """Logout as a user.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        zen_store.logout()
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
