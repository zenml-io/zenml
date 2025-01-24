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
"""Class for defining a pipeline schedule."""

from datetime import datetime, timedelta
from typing import Optional

from pydantic import (
    BaseModel,
    ValidationInfo,
    field_validator,
    model_validator,
)

from zenml.logger import get_logger

logger = get_logger(__name__)


class Schedule(BaseModel):
    """Class for defining a pipeline schedule.

    Attributes:
        name: Optional name to give to the schedule. If not set, a default name
            will be generated based on the pipeline name and the current date
            and time.
        cron_expression: Cron expression for the pipeline schedule. If a value
            for this is set it takes precedence over the start time + interval.
        start_time: When the schedule should start. If this is a datetime object
            without any timezone, it is treated as a datetime in the local
            timezone.
        end_time: When the schedule should end. If this is a datetime object
            without any timezone, it is treated as a datetime in the local
            timezone.
        interval_second: datetime timedelta indicating the seconds between two
            recurring runs for a periodic schedule.
        catchup: Whether the recurring run should catch up if behind schedule.
            For example, if the recurring run is paused for a while and
            re-enabled afterward. If catchup=True, the scheduler will catch
            up on (backfill) each missed interval. Otherwise, it only
            schedules the latest interval if more than one interval is ready to
            be scheduled. Usually, if your pipeline handles backfill
            internally, you should turn catchup off to avoid duplicate backfill.
        run_once_start_time: When to run the pipeline once. If this is a
            datetime object without any timezone, it is treated as a datetime
            in the local timezone.
    """

    name: Optional[str] = None
    cron_expression: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval_second: Optional[timedelta] = None
    catchup: bool = False
    run_once_start_time: Optional[datetime] = None

    @field_validator(
        "start_time", "end_time", "run_once_start_time", mode="after"
    )
    @classmethod
    def _ensure_timezone(
        cls, value: Optional[datetime], info: ValidationInfo
    ) -> Optional[datetime]:
        """Ensures that all datetimes are timezone aware.

        Args:
            value: The datetime.
            info: The validation info.

        Returns:
            A timezone aware datetime or None.
        """
        if value and value.tzinfo is None:
            assert info.field_name
            logger.warning(
                "Your schedule `%s` is missing a timezone. It will be treated "
                "as a datetime in your local timezone.",
                info.field_name,
            )
            value = value.astimezone()

        return value

    @model_validator(mode="after")
    def _ensure_cron_or_periodic_schedule_configured(self) -> "Schedule":
        """Ensures that the cron expression or start time + interval are set.

        Returns:
            All schedule attributes.

        Raises:
            ValueError: If no cron expression or start time + interval were
                provided.
        """
        periodic_schedule = self.start_time and self.interval_second

        if self.cron_expression and periodic_schedule:
            logger.warning(
                "This schedule was created with a cron expression as well as "
                "values for `start_time` and `interval_seconds`. The resulting "
                "behavior depends on the concrete orchestrator implementation "
                "but will usually ignore the interval and use the cron "
                "expression."
            )

            return self
        elif self.cron_expression and self.run_once_start_time:
            logger.warning(
                "This schedule was created with a cron expression as well as "
                "a value for `run_once_start_time`. The resulting behavior "
                "depends on the concrete orchestrator implementation but will "
                "usually ignore the `run_once_start_time`."
            )
            return self
        elif (
            self.cron_expression
            or periodic_schedule
            or self.run_once_start_time
        ):
            return self
        else:
            raise ValueError(
                "Either a cron expression, a start time and interval seconds "
                "or a run once start time "
                "need to be set for a valid schedule."
            )
