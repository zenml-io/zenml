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

from fastapi import APIRouter, HTTPException, Security, status

from zenml.constants import (
    ACTIVATE,
    API,
    DEACTIVATE,
    EMAIL_ANALYTICS,
    ROLES,
    USERS,
    VERSION_1,
)
from zenml.enums import PermissionType
from zenml.exceptions import IllegalOperationError, NotAuthorizedError
from zenml.logger import get_logger
from zenml.models import (
    RoleAssignmentRequestModel,
    RoleAssignmentResponseModel,
    UserRequestModel,
    UserResponseModel,
    UserUpdateModel,
)
from zenml.zen_server.auth import (
    AuthContext,
    authenticate_credentials,
    authorize,
)
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + USERS,
    tags=["users"],
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
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[UserResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_users(
    name: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[UserResponseModel]:
    """Returns a list of all users.

    Args:
        name: Optionally filter by name

    Returns:
        A list of all users.
    """
    return zen_store().list_users(name=name)


@router.post(
    "",
    response_model=UserResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_user(
    user: UserRequestModel,
    assign_default_role: bool = True,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> UserResponseModel:
    """Creates a user.

    # noqa: DAR401

    Args:
        user: User to create.
        assign_default_role: Whether the initial role should be assigned to the
            new user.

    Returns:
        The created user.
    """
    # Two ways of creating a new user:
    # 1. Create a new user with a password and have it immediately active
    # 2. Create a new user without a password and have it activated at a
    # later time with an activation token

    token: Optional[str] = None
    if user.password is None:
        user.active = False
        token = user.generate_activation_token()
    else:
        user.active = True
    new_user = zen_store().create_user(user)

    # For the time being all users are implicitly assigned the admin role
    if assign_default_role:
        zen_store().create_role_assignment(
            RoleAssignmentRequestModel(
                role=zen_store()._admin_role.id,
                user=new_user.id,
            )
        )

    # add back the original unhashed activation token, if generated, to
    # send it back to the client
    if token:
        new_user.activation_token = token
    return new_user


@router.get(
    "/{user_name_or_id}",
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_user(
    user_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> UserResponseModel:
    """Returns a specific user.

    Args:
        user_name_or_id: Name or ID of the user.

    Returns:
        A specific user.
    """
    return zen_store().get_user(user_name_or_id=user_name_or_id)


@router.put(
    "/{user_name_or_id}",
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_user(
    user_name_or_id: Union[str, UUID],
    user_update: UserUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> UserResponseModel:
    """Updates a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        user_update: the user to use for the update.

    Returns:
        The updated user.
    """
    user = zen_store().get_user(user_name_or_id)

    return zen_store().update_user(
        user_id=user.id,
        user_update=user_update,
    )


@activation_router.put(
    "/{user_name_or_id}" + ACTIVATE,
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def activate_user(
    user_name_or_id: Union[str, UUID],
    user_update: UserUpdateModel,
) -> UserResponseModel:
    """Activates a specific user.

    Args:
        user_name_or_id: Name or ID of the user.
        user_update: the user to use for the update.

    Returns:
        The updated user.

    Raises:
        HTTPException: If the user is not authorized to activate the user.
    """
    user = zen_store().get_user(user_name_or_id)

    auth_context = authenticate_credentials(
        user_name_or_id=user_name_or_id,
        activation_token=user_update.activation_token,
    )
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user_update.active = True
    user_update.activation_token = None
    return zen_store().update_user(user_id=user.id, user_update=user_update)


@router.put(
    "/{user_name_or_id}" + DEACTIVATE,
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def deactivate_user(
    user_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> UserResponseModel:
    """Deactivates a user and generates a new activation token for it.

    Args:
        user_name_or_id: Name or ID of the user.

    Returns:
        The generated activation token.
    """
    user = zen_store().get_user(user_name_or_id)

    user_update = UserUpdateModel(active=False)
    token = user_update.generate_activation_token()
    user = zen_store().update_user(user_id=user.id, user_update=user_update)
    # add back the original unhashed activation token
    user.activation_token = token
    return user


@router.delete(
    "/{user_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_user(
    user_name_or_id: Union[str, UUID],
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
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
            "You cannot delete the user account currently used to authenticate "
            "to the ZenML server. If you wish to delete this account, "
            "please authenticate with another account or contact your ZenML "
            "administrator."
        )
    zen_store().delete_user(user_name_or_id=user_name_or_id)


@router.put(
    "/{user_name_or_id}" + EMAIL_ANALYTICS,
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def email_opt_in_response(
    user_name_or_id: Union[str, UUID],
    user_response: UserUpdateModel,
    auth_context: AuthContext = Security(authorize, scopes=[PermissionType.ME]),
) -> UserResponseModel:
    """Sets the response of the user to the email prompt.

    Args:
        user_name_or_id: Name or ID of the user.
        user_response: User Response to email prompt
        auth_context: The authentication context of the user

    Returns:
        The updated user.

    Raises:
        NotAuthorizedError: if the user does not have the required
            permissions
    """
    user = zen_store().get_user(user_name_or_id)

    if str(auth_context.user.id) == str(user_name_or_id):
        user_update = UserUpdateModel(
            email=user_response.email,
            email_opted_in=user_response.email_opted_in,
        )

        return zen_store().update_user(user_id=user.id, user_update=user_update)
    else:
        raise NotAuthorizedError(
            "Users can not opt in on behalf of another " "user."
        )


@router.get(
    "/{user_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignments_for_user(
    user_name_or_id: Union[str, UUID],
    project_name_or_id: Optional[Union[str, UUID]] = None,
    role_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[RoleAssignmentResponseModel]:
    """Returns a list of all roles that are assigned to a user.

    Args:
        user_name_or_id: Name or ID of the user.
        project_name_or_id: If provided, only list roles that are limited to
            the given project.
        role_name_or_id: If provided, only list assignments of the given
            role

    Returns:
        A list of all roles that are assigned to a user.
    """
    return zen_store().list_role_assignments(
        user_name_or_id=user_name_or_id,
        project_name_or_id=project_name_or_id,
        role_name_or_id=role_name_or_id,
    )


@current_user_router.get(
    "/current-user",
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_current_user(
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> UserResponseModel:
    """Returns the model of the authenticated user.

    Args:
        auth_context: The authentication context.

    Returns:
        The model of the authenticated user.
    """
    return auth_context.user


@current_user_router.put(
    "/current-user",
    response_model=UserResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_myself(
    user: UserUpdateModel,
    auth_context: AuthContext = Security(authorize, scopes=[PermissionType.ME]),
) -> UserResponseModel:
    """Updates a specific user.

    Args:
        user: the user to use for the update.
        auth_context: The authentication context.

    Returns:
        The updated user.
    """
    return zen_store().update_user(
        user_id=auth_context.user.id, user_update=user
    )
