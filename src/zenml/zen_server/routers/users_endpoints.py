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

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import INVITE_TOKEN, ROLES, USERS, VERSION_1
from zenml.exceptions import EntityExistsError
from zenml.models import RoleAssignmentModel, RoleModel, UserModel
from zenml.zen_server.utils import (
    authorize,
    conflict,
    error_detail,
    error_response,
    not_found,
    zen_store,
)

router = APIRouter(
    prefix=VERSION_1 + USERS,
    tags=["users"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[UserModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_users() -> List[UserModel]:
    """Returns a list of all users.

    Returns:
        A list of all users.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_users()
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/",
    response_model=UserModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_user(user: UserModel) -> UserModel:
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
        return zen_store.create_user(user)
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
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_user(user_id: str) -> UserModel:
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
        return zen_store.get_user(user_name_or_id=user_id)
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
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_user(user_id: str, user: UserModel) -> UserModel:
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
        not_found: when user does not exist
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
    "/{user_id}" + ROLES,
    response_model=List[RoleModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_role_assignments_for_user(
    user_id: str,
) -> List[RoleAssignmentModel]:
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
        return zen_store.list_role_assignments(user_id=user_id)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{user_id}" + ROLES,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def assign_role(user_id: str, role_id: str, project_id: str) -> None:
    """Assign a role to a user for all resources within a given project or globally.

    Args:
        user_id: ID of the user.
        role_id: The ID of the role to assign to the user.
        project_id: ID of the project in which to assign the role to the user.

    Raises:
        not_found: when user does not exist
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    # TODO: Delete when no longer needed
    # role_name = data["role_name"]
    # entity_name = data["entity_name"]
    # project_name = data.get("project_name")
    # is_user = data.get("is_user", True)

    try:
        zen_store.assign_role(
            role_id=role_id,
            user_or_team_id=user_id,
            is_user=True,
            project_id=project_id,
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
    "/{user_id}" + INVITE_TOKEN,
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
    "/{user_id}" + INVITE_TOKEN,
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
    "/{user_id}" + ROLES + "/{role_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def unassign_role(user_id: str, role_id: str, project_id: str) -> None:
    """Remove a users role within a project or globally.

    Args:
        user_id: ID of the user.
        role_id: ID of the role.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store._revoke_role(
            role_id=role_id,
            user_or_team_id=user_id,
            is_user=True,
            project_id=project_id,
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
