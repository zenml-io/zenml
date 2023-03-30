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
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, TEAM_ROLE_ASSIGNMENTS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import (
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentRequestModel,
    TeamRoleAssignmentResponseModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + TEAM_ROLE_ASSIGNMENTS,
    tags=["team_role_assignments"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[TeamRoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_team_role_assignments(
    team_role_assignment_filter_model: TeamRoleAssignmentFilterModel = Depends(
        make_dependable(TeamRoleAssignmentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[TeamRoleAssignmentResponseModel]:
    """Returns a list of all role assignments.

    Args:
        team_role_assignment_filter_model: filter models for team role assignments


    Returns:
        List of all role assignments.
    """
    return zen_store().list_team_role_assignments(
        team_role_assignment_filter_model=team_role_assignment_filter_model
    )


@router.post(
    "",
    response_model=TeamRoleAssignmentResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_team_role_assignment(
    role_assignment: TeamRoleAssignmentRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> TeamRoleAssignmentResponseModel:
    """Creates a role assignment.

    # noqa: DAR401

    Args:
        role_assignment: Role assignment to create.

    Returns:
        The created role assignment.
    """
    return zen_store().create_team_role_assignment(
        team_role_assignment=role_assignment
    )


@router.get(
    "/{role_assignment_id}",
    response_model=TeamRoleAssignmentResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_team_role_assignment(
    role_assignment_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> TeamRoleAssignmentResponseModel:
    """Returns a specific role assignment.

    Args:
        role_assignment_id: Name or ID of the role assignment.

    Returns:
        A specific role assignment.
    """
    return zen_store().get_team_role_assignment(
        team_role_assignment_id=role_assignment_id
    )


@router.delete(
    "/{role_assignment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_team_role_assignment(
    role_assignment_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific role.

    Args:
        role_assignment_id: The ID of the role assignment.
    """
    zen_store().delete_team_role_assignment(
        team_role_assignment_id=role_assignment_id
    )
