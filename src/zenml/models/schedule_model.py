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

import datetime
from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.config.schedule import Schedule
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)

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


class ScheduleResponseModel(ScheduleBaseModel, ProjectScopedResponseModel):
    """Schedule response model with project and user hydrated."""


# ------- #
# REQUEST #
# ------- #


class ScheduleRequestModel(ScheduleBaseModel, ProjectScopedRequestModel):
    """Schedule request model."""


# ------ #
# UPDATE #
# ------ #


class ScheduleUpdateModel(BaseModel):
    """Schedule update model."""

    name: Optional[str] = None
    active: Optional[bool] = None
    cron_expression: Optional[str] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    interval_second: Optional[datetime.timedelta] = None
    catchup: Optional[bool] = None
