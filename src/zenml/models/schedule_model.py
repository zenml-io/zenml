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
"""Model definition for pipeline run schedules."""

from datetime import datetime, timedelta
from typing import ClassVar, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.schedule import Schedule
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.filter_models import ShareableWorkspaceScopedFilterModel

# ---- #
# BASE #
# ---- #


class ScheduleBaseModel(Schedule, BaseModel):
    """Domain model for schedules."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["id"]

    name: str
    active: bool
    orchestrator_id: Optional[UUID]
    pipeline_id: Optional[UUID]


# -------- #
# RESPONSE #
# -------- #


class ScheduleResponseModel(ScheduleBaseModel, WorkspaceScopedResponseModel):
    """Schedule response model with workspace and user hydrated."""


# ------ #
# FILTER #
# ------ #


class ScheduleFilterModel(ShareableWorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Users."""

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace scope of the schedule."
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User that created the schedule"
    )
    pipeline_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Pipeline that the schedule is attached to."
    )
    orchestrator_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Orchestrator that the schedule is attached to.",
    )
    active: Optional[bool] = Field(
        default=None,
        description="If the schedule is active",
    )
    cron_expression: Optional[str] = Field(
        default=None,
        description="The cron expression, describing the schedule",
    )
    start_time: Optional[Union[datetime, str]] = Field(
        default=None, description="Start time"
    )
    end_time: Optional[Union[datetime, str]] = Field(
        default=None, description="End time"
    )
    interval_second: Optional[Optional[float]] = Field(
        default=None,
        description="The repetition interval in seconds",
    )
    catchup: Optional[bool] = Field(
        default=None,
        description="Whether or not the schedule is set to catchup past missed "
        "events",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the schedule",
    )


# ------- #
# REQUEST #
# ------- #


class ScheduleRequestModel(ScheduleBaseModel, WorkspaceScopedRequestModel):
    """Schedule request model."""


# ------ #
# UPDATE #
# ------ #


class ScheduleUpdateModel(BaseModel):
    """Schedule update model."""

    name: Optional[str] = None
    active: Optional[bool] = None
    cron_expression: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval_second: Optional[timedelta] = None
    catchup: Optional[bool] = None
