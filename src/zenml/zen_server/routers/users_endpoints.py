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

from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import SecretStr

from zenml.constants import (
    ACTIVATE,
    API,
    DEACTIVATE,
    EMAIL_ANALYTICS,
    ROLES,
    USERS,
    VERSION_1,
)
from zenml.exceptions import IllegalOperationError
from zenml.logger import get_logger
from zenml.models import RoleAssignmentModel, UserModel
from zenml.zen_server.auth import (
    AuthContext,
    authenticate_credentials,
    authorize,
)
from zenml.zen_server.models.user_management_models import (
    ActivateUserRequest,
    CreateUserRequest,
    CreateUserResponse,
    DeactivateUserResponse,
    EmailOptInModel,
    UpdateUserRequest,
)
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + USERS,
    tags=["users"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


activation_router = APIRouter(
    prefix=API + VERSION_1 + USERS,
    tags=["users"],
    responses={401: error_response},
)


current_user_router = APIRouter(
    prefix=API + VERSION_1,
    tags=["users"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[UserModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_users() -> List[UserModel]:
    """Returns a list of all users.

    Returns:
        A list of all users.
    """
    return zen_store().list_users()


@router.post(
    "",
    response_model=CreateUserResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_user(user: CreateUserRequest) -> CreateUserResponse:
    """Creates a user.

    # noqa: DAR401

    Args:
        user: User to create.

    Returns:
        The created user.
    """
    # Two ways of creating a new user:
    # 1. Create a new user with a password and have it immediately active
    # 2. Create a new user without a password and have it activated at a
    # later time with an activation token

    user_model = user.to_model()
    token: Optional[SecretStr] = None
    if user.password is None:
        user_model.active = False
        token = user_model.generate_activation_token()
    else:
        user_model.active = True
    new_user = zen_store().create_user(user_model)
    # add back the original unhashed activation token, if generated, to
    # send it back to the client
    new_user.activation_token = token
    return CreateUserResponse.from_model(new_user)


@router.get(
    "/{user_name_or_id}",
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_user(user_name_or_id: Union[str, UUID]) -> UserModel:
    """Returns a specific user.

    Args:
        user_name_or_id: Name or ID of the user.

    Returns:
        A specific user.
    """
    return zen_store().get_user(user_name_or_id=user_name_or_id)


@router.put(
    "/{user_name_or_id}",
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_user(
    user_name_or_id: Union[str, UUID], user: UpdateUserRequest
) -> UserModel:
    """Updates a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        user: the user to to use for the update.

    Returns:
        The updated user.
    """
    existing_user = zen_store().get_user(user_name_or_id)
    user_model = user.apply_to_model(existing_user)
    return zen_store().update_user(user_model)


@activation_router.put(
    "/{user_name_or_id}" + ACTIVATE,
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def activate_user(
    user_name_or_id: Union[str, UUID], user: ActivateUserRequest
) -> UserModel:
    """Activates a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        user: the user to to use for the update.

    Returns:
        The updated user.

    Raises:
        HTTPException: If the user is not authorized to activate the user.
    """
    auth_context = authenticate_credentials(
        user_name_or_id=user_name_or_id,
        activation_token=user.activation_token,
    )
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user_model = user.apply_to_model(auth_context.user)
    user_model.active = True
    user_model.activation_token = None
    return zen_store().update_user(user_model)


@router.put(
    "/{user_name_or_id}" + DEACTIVATE,
    response_model=DeactivateUserResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def deactivate_user(
    user_name_or_id: Union[str, UUID]
) -> DeactivateUserResponse:
    """Deactivates a user and generates a new activation token for it.

    Args:
        user_name_or_id: Name or ID of the user.

    Returns:
        The generated activation token.
    """
    user = zen_store().get_user(user_name_or_id)
    user.active = False
    token = user.generate_activation_token()
    user = zen_store().update_user(user=user)
    # add back the original unhashed activation token
    user.activation_token = token
    return DeactivateUserResponse.from_model(user)


@router.delete(
    "/{user_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_user(
    user_name_or_id: Union[str, UUID],
    auth_context: AuthContext = Depends(authorize),
) -> None:
    """Deletes a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        auth_context: The authentication context.

    Raises:
        IllegalOperationError: If the user is not authorized to delete the user.
    """
    user = zen_store().get_user(user_name_or_id)

    if auth_context.user.name == user.name:
        raise IllegalOperationError(
            "You cannot delete yourself. If you wish to delete your active "
            "user account, please contact your ZenML administrator."
        )
    zen_store().delete_user(user_name_or_id=user_name_or_id)


@router.put(
    "/{user_name_or_id}" + EMAIL_ANALYTICS,
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def email_opt_in_response(
    user_name_or_id: Union[str, UUID], user_response: EmailOptInModel
) -> UserModel:
    """Deactivates a user and generates a new activation token for it.

    Args:
        user_name_or_id: Name or ID of the user.
        user_response: User Response to email prompt

    Returns:
        The updated user.
    """
    return zen_store().user_email_opt_in(
        user_name_or_id=user_name_or_id,
        email=user_response.email,
        user_opt_in_response=user_response.email_opted_in,
    )


@router.get(
    "/{user_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignments_for_user(
    user_name_or_id: Union[str, UUID],
    project_name_or_id: Optional[Union[str, UUID]] = None,
) -> List[RoleAssignmentModel]:
    """Returns a list of all roles that are assigned to a user.

    Args:
        user_name_or_id: Name or ID of the user.
        project_name_or_id: If provided, only list roles that are limited to
            the given project.

    Returns:
        A list of all roles that are assigned to a user.
    """
    return zen_store().list_role_assignments(
        user_name_or_id=user_name_or_id,
        project_name_or_id=project_name_or_id,
    )


@router.post(
    "/{user_name_or_id}" + ROLES,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def assign_role(
    user_name_or_id: Union[str, UUID],
    role_name_or_id: Union[str, UUID],
    project_name_or_id: Optional[Union[str, UUID]] = None,
) -> None:
    """Assign a role to a user for all resources within a given project or globally.

    Args:
        role_name_or_id: The name or ID of the role to assign to the user.
        user_name_or_id: Name or ID of the user to which to assign the role.
        project_name_or_id: Name or ID of the project in which to assign the
            role to the user. If this is not provided, the role will be
            assigned globally.
    """
    zen_store().assign_role(
        role_name_or_id=role_name_or_id,
        user_or_team_name_or_id=user_name_or_id,
        is_user=True,
        project_name_or_id=project_name_or_id,
    )


@router.delete(
    "/{user_name_or_id}" + ROLES + "/{role_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def unassign_role(
    user_name_or_id: Union[str, UUID],
    role_name_or_id: Union[str, UUID],
    project_name_or_id: Optional[Union[str, UUID]],
) -> None:
    """Remove a users role within a project or globally.

    Args:
        user_name_or_id: Name or ID of the user.
        role_name_or_id: Name or ID of the role.
        project_name_or_id: Name or ID of the project. If this is not
            provided, the role will be revoked globally.
    """
    zen_store().revoke_role(
        role_name_or_id=role_name_or_id,
        user_or_team_name_or_id=user_name_or_id,
        is_user=True,
        project_name_or_id=project_name_or_id,
    )


@current_user_router.get(
    "/current-user",
    response_model=UserModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_current_user(
    auth_context: AuthContext = Depends(authorize),
) -> UserModel:
    """Returns the model of the authenticated user.

    Args:
        auth_context: The authentication context.

    Returns:
        The model of the authenticated user.
    """
    return auth_context.user
