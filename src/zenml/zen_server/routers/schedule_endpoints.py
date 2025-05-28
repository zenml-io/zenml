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
"""Endpoint definitions for pipeline run schedules."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, SCHEDULES, VERSION_1
from zenml.models import (
    Page,
    ScheduleFilter,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + SCHEDULES,
    tags=["schedules"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + SCHEDULES,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["schedules"],
)
@async_fastapi_endpoint_wrapper
def create_schedule(
    schedule: ScheduleRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    auth_context: AuthContext = Security(authorize),
) -> ScheduleResponse:
    """Creates a schedule.

    Args:
        schedule: Schedule to create.
        project_name_or_id: Optional name or ID of the project.
        auth_context: Authentication context.

    Returns:
        The created schedule.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        schedule.project = project.id

    # NOTE: no RBAC is enforced currently for schedules, but we're
    # keeping the RBAC checks here for consistency
    return verify_permissions_and_create_entity(
        request_model=schedule,
        create_method=zen_store().create_schedule,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + SCHEDULES,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["schedules"],
)
@async_fastapi_endpoint_wrapper
def list_schedules(
    schedule_filter_model: ScheduleFilter = Depends(
        make_dependable(ScheduleFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ScheduleResponse]:
    """Gets a list of schedules.

    Args:
        schedule_filter_model: Filter model used for pagination, sorting,
            filtering
        project_name_or_id: Optional name or ID of the project.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of schedule objects.
    """
    if project_name_or_id:
        schedule_filter_model.project = project_name_or_id

    return zen_store().list_schedules(
        schedule_filter_model=schedule_filter_model,
        hydrate=hydrate,
    )


@router.get(
    "/{schedule_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_schedule(
    schedule_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ScheduleResponse:
    """Gets a specific schedule using its unique id.

    Args:
        schedule_id: ID of the schedule to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific schedule object.
    """
    return zen_store().get_schedule(
        schedule_id=schedule_id,
        hydrate=hydrate,
    )


@router.put(
    "/{schedule_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_schedule(
    schedule_id: UUID,
    schedule_update: ScheduleUpdate,
    _: AuthContext = Security(authorize),
) -> ScheduleResponse:
    """Updates the attribute on a specific schedule using its unique id.

    Args:
        schedule_id: ID of the schedule to get.
        schedule_update: the model containing the attributes to update.

    Returns:
        The updated schedule object.
    """
    return zen_store().update_schedule(
        schedule_id=schedule_id,
        schedule_update=schedule_update,
    )


@router.delete(
    "/{schedule_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_schedule(
    schedule_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific schedule using its unique id.

    Args:
        schedule_id: ID of the schedule to delete.
    """
    zen_store().delete_schedule(schedule_id=schedule_id)
