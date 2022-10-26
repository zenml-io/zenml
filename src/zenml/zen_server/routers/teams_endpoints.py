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
"""Endpoint definitions for teams and team membership."""
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends

from zenml.constants import API, ROLES, TEAMS, VERSION_1
from zenml.models import TeamModel
from zenml.models.user_management_models import RoleAssignmentModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.models.user_management_models import (
    CreateTeamRequest,
    UpdateTeamRequest,
)
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + TEAMS,
    tags=["teams"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[TeamModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_teams() -> List[TeamModel]:
    """Returns a list of all teams.

    Returns:
        List of all teams.
    """
    return zen_store().list_teams()


@router.post(
    "",
    response_model=TeamModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_team(team: CreateTeamRequest) -> TeamModel:
    """Creates a team.

    # noqa: DAR401

    Args:
        team: Team to create.

    Returns:
        The created team.
    """
    return zen_store().create_team(team=team.to_model())


@router.get(
    "/{team_name_or_id}",
    response_model=TeamModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_team(team_name_or_id: Union[str, UUID]) -> TeamModel:
    """Returns a specific team.

    Args:
        team_name_or_id: Name or ID of the team.

    Returns:
        A specific team.
    """
    return zen_store().get_team(team_name_or_id=team_name_or_id)


@router.put(
    "/{team_name_or_id}",
    response_model=TeamModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def update_team(
    team_name_or_id: Union[str, UUID], team_update: UpdateTeamRequest
) -> TeamModel:
    """Updates a team.

    # noqa: DAR401

    Args:
        team_name_or_id: Name or ID of the team.
        team_update: Team update.

    Returns:
        The created team.
    """
    team_in_db = zen_store().get_team(team_name_or_id)
    return zen_store().update_team(team=team_update.apply_to_model(team_in_db))


@router.delete(
    "/{team_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_team(team_name_or_id: Union[str, UUID]) -> None:
    """Deletes a specific team.

    Args:
        team_name_or_id: Name or ID of the team.
    """
    zen_store().delete_team(team_name_or_id=team_name_or_id)


@router.get(
    "/{team_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignments_for_team(
    team_name_or_id: Union[str, UUID],
    project_name_or_id: Optional[Union[str, UUID]] = None,
) -> List[RoleAssignmentModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        team_name_or_id: Name or ID of the team.
        project_name_or_id: If provided, only list roles that are limited to
            the given project.

    Returns:
        A list of all roles that are assigned to a team.
    """
    return zen_store().list_role_assignments(
        team_name_or_id=team_name_or_id,
        project_name_or_id=project_name_or_id,
    )
