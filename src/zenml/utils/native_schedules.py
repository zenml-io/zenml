#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""PRO native schedules utility functions."""

import math
from datetime import datetime, timedelta, timezone

from croniter import croniter

from zenml.enums import ScheduleEngine
from zenml.models import SchedulePayload


def next_occurrence_for_interval(
    interval: int | float, start: datetime, base: datetime | None = None
) -> datetime:
    """Calculate the next occurrence based on interval based schedules.

    Args:
        interval: The difference (in seconds) between two occurrences.
        start: The first occurrence.
        base: The base used to calculate the next occurrence.

    Returns:
        The next occurrence datatime.
    """
    start = start.replace(tzinfo=timezone.utc)

    if not base:
        base = datetime.now(tz=timezone.utc).replace(second=0, microsecond=0)
    else:
        base = base.replace(tzinfo=timezone.utc)

    in_between_intervals = math.floor(
        (base - start).total_seconds() / interval
    )

    return (
        start + timedelta(seconds=(in_between_intervals + 1) * interval)
    ).replace(second=0, microsecond=0)


def next_occurrence_for_cron(
    expression: str, base: datetime | None = None
) -> datetime:
    """Calculate the next occurrence based on interval based schedules.

    Args:
        expression: The cron expression.
        base: The base used to calculate the next occurrence.

    Returns:
        The next occurrence datatime.
    """
    if not base:
        base = datetime.now(tz=timezone.utc)
    else:
        base = base.replace(tzinfo=timezone.utc)

    return croniter(expression, base).get_next(datetime)


def calculate_first_occurrence(schedule: SchedulePayload) -> datetime | None:
    """Calculate the first occurrence of a schedule.

    Args:
        schedule: A schedule payload object.

    Returns:
        The first occurrence of a schedule.
    """
    if not schedule.engine == ScheduleEngine.native:
        return None

    if schedule.cron_expression:
        next_occurrence = next_occurrence_for_cron(
            expression=schedule.cron_expression,
            base=schedule.start_time or datetime.now(timezone.utc),
        )
    elif schedule.start_time and schedule.interval:
        next_occurrence = next_occurrence_for_interval(
            interval=schedule.interval,
            start=schedule.start_time,
        )
    elif schedule.run_once_start_time:
        next_occurrence = schedule.run_once_start_time
    else:
        return None

    return next_occurrence
