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
"""Endpoint definitions for users."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from zenml.constants import ACTIVATE, DEACTIVATE, ROLES, USERS, VERSION_1
from zenml.exceptions import (
    EntityExistsError,
    NotAuthorizedError,
    ValidationError,
)
from zenml.logger import get_logger
from zenml.models import RoleAssignmentModel, UserModel
from zenml.utils.uuid_utils import (
    parse_name_or_uuid,
    parse_optional_name_or_uuid,
)
from zenml.zen_server.auth import authenticate_credentials, authorize
from zenml.zen_server.models.user_management_models import (
    ActivateUserRequest,
    DeactivateUserResponse,
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
)
from zenml.zen_server.utils import (
    conflict,
    error_detail,
    error_response,
    not_found,
    zen_store,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix=VERSION_1 + USERS,
    tags=["users"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


activation_router = APIRouter(
    prefix=VERSION_1 + USERS,
    tags=["users"],
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
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/",
    response_model=CreateUserResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_user(user: CreateUserRequest) -> CreateUserResponse:
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
        # Two ways of creating a new user:
        # 1. Create a new user with a password and have it immediately active
        # 2. Create a new user without a password and have it activated at a
        # later time with an activation token

        user_model = user.to_model()
        token: Optional[str] = None
        if user.password is None:
            user_model.active = False
            token = user_model.generate_activation_token()
            user_model.hash_activation_token()
        else:
            user_model.active = True
            user_model.hash_password()
        new_user = zen_store.create_user(user_model)
        # add back the original un-hashed activation token, if generated, to
        # send it back to the client
        new_user.activation_token = token
        return CreateUserResponse.from_model(new_user)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except EntityExistsError as error:
        raise conflict(error) from error


@router.get(
    "/{user_name_or_id}",
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_user(user_name_or_id: str) -> UserModel:
    """Returns a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        activation_token: Token to use for the invitation.

    Returns:
        A specific user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_user(
            user_name_or_id=parse_name_or_uuid(user_name_or_id)
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{user_name_or_id}",
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_user(
    user_name_or_id: str, user: UpdateUserRequest
) -> UserModel:
    """Updates a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        user: the user to to use for the update.

    Returns:
        The updated user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        existing_user = zen_store.get_user(parse_name_or_uuid(user_name_or_id))
        user_model = user.to_model(user=existing_user)
        if user.password is not None:
            user_model.hash_password()

        return zen_store.update_user(
            user=user_model
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@activation_router.put(
    "/{user_name_or_id}" + ACTIVATE,
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def activate_user(
    user_name_or_id: str, user: ActivateUserRequest
) -> UserModel:
    """Activates a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        user: the user to to use for the update.

    Returns:
        The updated user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        auth_context = authenticate_credentials(
            user_name_or_id=parse_name_or_uuid(user_name_or_id),
            activation_token=user.activation_token.get_secret_value(),
        )
        if auth_context is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        user_model = user.to_model(user=auth_context.user)
        user_model.hash_password()
        user_model.active = True
        user_model.activation_token = None
        return zen_store.update_user(
            user=user_model
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{user_name_or_id}" + DEACTIVATE,
    response_model=DeactivateUserResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def deactivate_user(user_name_or_id: str) -> UserModel:
    """Deactivates a user and generates a new activation token for it.

    Args:
        user_name_or_id: Name or ID of the user.

    Returns:
        The generated activation token.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        user = zen_store.get_user(parse_name_or_uuid(user_name_or_id))
        user.active = False
        token = user.generate_activation_token()
        user.hash_activation_token()
        user = zen_store.update_user(
            user=user
        )
        # add back the original un-hashed activation token, if generated, to
        # send it back to the client
        user.activation_token = token
        return DeactivateUserResponse.from_model(user)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{user_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_user(user_name_or_id: str) -> None:
    """Deletes a specific user.

    Args:
        user_name_or_id: Name or ID of the user.

    Raises:
        not_found: when user does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_user(
            user_name_or_id=parse_name_or_uuid(user_name_or_id)
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{user_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_role_assignments_for_user(
    user_name_or_id: str,
) -> List[RoleAssignmentModel]:
    """Returns a list of all roles that are assigned to a user.

    Args:
        user_name_or_id: Name or ID of the user.

    Returns:
        A list of all roles that are assigned to a user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_role_assignments(
            user_name_or_id=parse_name_or_uuid(user_name_or_id)
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    "/{user_name_or_id}" + ROLES,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def assign_role(
    role_name_or_id: str,
    user_name_or_id: str,
    project_name_or_id: Optional[str] = None,
) -> None:
    """Assign a role to a user for all resources within a given project or globally.

    Args:
        role_name_or_id: The name or ID of the role to assign to the user.
        user_name_or_id: Name or ID of the user to which to assign the role.
        project_name_or_id: Name or ID of the project in which to assign the
            role to the user. If this is not provided, the role will be
            assigned globally.

    Raises:
        not_found: when user does not exist
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.assign_role(
            role_name_or_id=parse_name_or_uuid(role_name_or_id),
            user_or_team_name_or_id=parse_name_or_uuid(user_name_or_id),
            is_user=True,
            project_name_or_id=parse_optional_name_or_uuid(project_name_or_id),
        )
    except KeyError as error:
        raise not_found(error) from error
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{user_name_or_id}" + ROLES + "/{role_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def unassign_role(
    user_name_or_id: str,
    role_name_or_id: str,
    project_name_or_id: Optional[str],
) -> None:
    """Remove a users role within a project or globally.

    Args:
        user_name_or_id: Name or ID of the user.
        role_name_or_id: Name or ID of the role.
        project_name_name_or_id: Name or ID of the project. If this is not
            provided, the role will be revoked globally.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.revoke_role(
            role_name_or_id=parse_name_or_uuid(role_name_or_id),
            user_or_team_name_or_id=parse_name_or_uuid(user_name_or_id),
            is_user=True,
            project_name_or_id=parse_optional_name_or_uuid(project_name_or_id),
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
