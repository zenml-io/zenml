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

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import INVITE_TOKEN, ROLES, USERS
from zenml.exceptions import EntityExistsError
from zenml.models import Role, User
from zenml.zen_server.utils import (
    authorize,
    conflict,
    error_detail,
    error_response,
    not_found,
    zen_store,
)

router = APIRouter(
    prefix=USERS,
    tags=["users"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[User],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_users(project_name: str, invite_token: str) -> List[User]:
    """Returns a list of all users.

    Args:
        project_name: Name of the project.
        invite_token: Token to use for the invitation.

    Returns:
        A list of all users.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_users(
            project_name=project_name, invite_token=invite_token
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/",
    response_model=User,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_user(user: User) -> User:
    """Creates a user.

    # noqa: DAR401

    Args:
        user: User to create.

    Returns:
        The created user.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_user(user.name)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except EntityExistsError as error:
        raise conflict(error) from error


@router.get(
    "/{user_id}",
    response_model=User,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_user(user_id: str, invite_token: str) -> User:
    """Returns a specific user.

    Args:
        user_id: ID of the user.
        invite_token: Token to use for the invitation.

    Returns:
        A specific user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_user(user_name=name)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


@router.put(
    "/{user_id}",
    response_model=User,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_user(user_id: str, user: User) -> User:
    """Updates a specific user.

    Args:
        user_id: ID of the user.
        user: the user to to use for the update.

    Returns:
        The updated user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_user(user_id, user)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


@router.delete(
    "/{user_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_user(user_id: str) -> None:
    """Deletes a specific user.

    Args:
        user_id: ID of the user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_user(user_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


@router.get(
    "/{user_id}}" + ROLES,
    response_model=List[Role],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_role_assignments_for_user(user_id: str) -> List[Role]:
    """Returns a list of all roles that are assigned to a user.

    Args:
        user_id: ID of the user.

    Returns:
        A list of all roles that are assigned to a user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_role_assignments_for_user(user_id)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{user_id}}" + ROLES,
    response_model=Role,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def assign_role(user_id: str, data: Dict[str, Any]) -> Role:
    """Assign a role to a user for all resources within a given project or globally.

    Args:
        user_id: ID of the user.
        data: Data relating to the role to assign to the user.

    Returns:
        The assigned role.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.assign_role(
            role_name=role_name,
            entity_name=entity_name,
            project_name=project_name,
            is_user=is_user,
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{user_id}}" + INVITE_TOKEN,
    response_model=str,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_invite_token(user_id: str) -> str:
    """Gets an invite token for a given user.

    If no invite token exists, one is created.

    Args:
        user_id: ID of the user.

    Returns:
        An invite token.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_invite_token(user_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{user_id}}" + INVITE_TOKEN,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def invalidate_invite_token(user_id: str) -> None:
    """Invalidates an invite token for a given user.

    Args:
        user_id: ID of the user.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.invalidate_invite_token(user_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{user_id}}" + ROLES + "/{role_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_user_role(
    user_id: str, role_id: str, project_name: str
) -> None:
    """Remove a users role within a project or globally.

    Args:
        user_id: ID of the user.
        role_id: ID of the role.
        project_name: Name of the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_role(
            user_id=user_id, role_id=role_id, project_name=project_name
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
