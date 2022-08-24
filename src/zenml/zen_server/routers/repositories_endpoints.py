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

from zenml.constants import REPOSITORIES
from zenml.repository import Repository
from zenml.zen_server.utils import authorize, error_detail, error_response, \
    zen_store

router = APIRouter(
    prefix=REPOSITORIES,
    tags=["repositories"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/{repository_id}",
    response_model=Repository,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_repository(repository_id: str) -> Repository:
    """Returns the requested repository.

    Args:
        repository_id: ID of the repository.

    Returns:
        The requested repository.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_repository(repository_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{repository_id}",
    response_model=Repository,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_repository(
    repository_id: str, repository: Repository
) -> Repository:
    """Updates the requested repository.

    Args:
        repository_id: ID of the repository.
        repository: Repository to use for the update.

    Returns:
        The updated repository.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_repository(repository_id, repository)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{repository_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_repository(repository_id: str) -> None:
    """Deletes the requested repository.

    Args:
        repository_id: ID of the repository.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_repository(repository_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
