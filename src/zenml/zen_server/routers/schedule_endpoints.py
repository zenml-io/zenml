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
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, SCHEDULES, VERSION_1
from zenml.enums import PermissionType
from zenml.models.page_model import Page
from zenml.models.schedule_model import (
    ScheduleFilterModel,
    ScheduleResponseModel,
    ScheduleUpdateModel,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + SCHEDULES,
    tags=["schedules"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[ScheduleResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_schedules(
    schedule_filter_model: ScheduleFilterModel = Depends(
        make_dependable(ScheduleFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ScheduleResponseModel]:
    """Gets a list of schedules.

    Args:
        schedule_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        List of schedule objects.
    """
    return zen_store().list_schedules(
        schedule_filter_model=schedule_filter_model
    )


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_schedule(
    schedule_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ScheduleResponseModel:
    """Gets a specific schedule using its unique id.

    Args:
        schedule_id: ID of the schedule to get.

    Returns:
        A specific schedule object.
    """
    return zen_store().get_schedule(schedule_id=schedule_id)


@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_schedule(
    schedule_id: UUID,
    schedule_update: ScheduleUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ScheduleResponseModel:
    """Updates the attribute on a specific schedule using its unique id.

    Args:
        schedule_id: ID of the schedule to get.
        schedule_update: the model containing the attributes to update.

    Returns:
        The updated schedule object.
    """
    return zen_store().update_schedule(
        schedule_id=schedule_id, schedule_update=schedule_update
    )


@router.delete(
    "/{schedule_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_schedule(
    schedule_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific schedule using its unique id.

    Args:
        schedule_id: ID of the schedule to delete.
    """
    zen_store().delete_schedule(schedule_id=schedule_id)
