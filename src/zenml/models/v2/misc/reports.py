#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

from datetime import datetime
from typing import Dict

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel

from zenml.enums import DurationType


class ReportRequest(BaseModel):
    """Request model for a report."""

    duration_type: DurationType
    duration_length: int

    @property
    def time_format(self) -> str:
        """The `time_format` property.

        Raises:
            ValueError: in case self.duration_type is misconfigured.

        Returns:
            the correct time format for the query based on the duration type.
        """
        if self.duration_type == DurationType.YEAR:
            return "%Y"
        elif self.duration_type == DurationType.MONTH:
            return "%m.%Y"
        elif self.duration_type == DurationType.DAY:
            return "%d.%m.%Y"
        elif self.duration_type == DurationType.HOUR:
            return "%d.%m.%Y,%H:00"
        elif self.duration_type == DurationType.MINUTE:
            return "%d.%m.%Y,%H:%M"
        else:
            raise ValueError("The `duration_type` needs to be a DurationType.")

    @property
    def time_limit(self) -> datetime:
        """The `time_limit` property.

        Raises:
            ValueError: in case self.duration_type is misconfigured.

        Returns:
            Computes and returns the point in time when the report should start.
        """
        now = datetime.now()
        if self.duration_type == DurationType.YEAR:
            past = now - relativedelta(years=self.duration_length)
            return datetime(year=past.year, month=1, day=1)

        elif self.duration_type == DurationType.MONTH:
            past = now - relativedelta(months=self.duration_length)
            return datetime(year=past.year, month=past.month, day=1)

        elif self.duration_type == DurationType.DAY:
            past = now - relativedelta(days=self.duration_length)
            return datetime(year=past.year, month=past.month, day=past.day)

        elif self.duration_type == DurationType.HOUR:
            past = now - relativedelta(hours=self.duration_length)
            return datetime(
                year=past.year, month=past.month, day=past.day, hour=past.hour
            )

        elif self.duration_type == DurationType.MINUTE:
            past = now - relativedelta(hours=self.duration_length)
            return datetime(
                year=past.year,
                month=past.month,
                day=past.day,
                hour=past.hour,
                minute=past.minute,
            )
        else:
            raise ValueError("The `duration_type` needs to be a DurationType.")


class ReportResponse(BaseModel):
    """Response model for a report"""

    total: int
    results: Dict[str, int]
