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
"""Endpoint definitions for role assignments."""
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, ROLE_ASSIGNMENTS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import RoleAssignmentRequestModel, RoleAssignmentResponseModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + ROLE_ASSIGNMENTS,
    tags=["role_assignments"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[RoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_role_assignments(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    role_name_or_id: Optional[Union[str, UUID]] = None,
    team_name_or_id: Optional[Union[str, UUID]] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[RoleAssignmentResponseModel]:
    """Returns a list of all role assignments.

    Args:
        project_name_or_id: If provided, only list assignments for the given
            project
        role_name_or_id: If provided, only list assignments of the given
            role
        team_name_or_id: If provided, only list assignments for the given
            team
        user_name_or_id: If provided, only list assignments for the given
            user

    Returns:
        List of all role assignments.
    """
    return zen_store().list_role_assignments(
        project_name_or_id=project_name_or_id,
        role_name_or_id=role_name_or_id,
        team_name_or_id=team_name_or_id,
        user_name_or_id=user_name_or_id,
    )


@router.post(
    "",
    response_model=RoleAssignmentResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_role_assignment(
    role_assignment: RoleAssignmentRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> RoleAssignmentResponseModel:
    """Creates a role assignment.

    # noqa: DAR401

    Args:
        role_assignment: Role assignment to create.

    Returns:
        The created role assignment.
    """
    return zen_store().create_role_assignment(role_assignment=role_assignment)


@router.get(
    "/{role_assignment_id}",
    response_model=RoleAssignmentResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignment(
    role_assignment_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> RoleAssignmentResponseModel:
    """Returns a specific role assignment.

    Args:
        role_assignment_id: Name or ID of the role assignment.

    Returns:
        A specific role assignment.
    """
    return zen_store().get_role_assignment(
        role_assignment_id=role_assignment_id
    )


@router.delete(
    "/{role_assignment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_role_assignment(
    role_assignment_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific role.

    Args:
        role_assignment_id: The ID of the role assignment.
    """
    zen_store().delete_role_assignment(role_assignment_id=role_assignment_id)
