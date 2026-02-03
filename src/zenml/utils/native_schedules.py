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


def next_occurrence_for_interval(
    interval: int | float, start: datetime, base: datetime | None = None
) -> datetime:
    """Calculate the next occurrence based on interval based schedules.

    Args:
        interval: The difference (in seconds) between two occurrences.
        start: The first occurrence.
        base: The base used to calculate the next occurrence.

    Returns:
        The next occurrence datetime.
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
        The next occurrence datetime.
    """
    if not base:
        base = datetime.now(tz=timezone.utc)
    else:
        base = base.replace(tzinfo=timezone.utc)

    return croniter(expression, base).get_next(datetime)


def calculate_first_occurrence(
    cron_expression: str | None = None,
    interval: int | None = None,
    start_time: datetime | None = None,
    run_once_start_time: datetime | None = None,
) -> datetime | None:
    """Calculate the first occurrence of a schedule.

    Args:
        cron_expression: The cron expression.
        interval: The interval in seconds.
        start_time: The start time.
        run_once_start_time: The run once start time.

    Returns:
        The first occurrence of a schedule.
    """
    now_plus_1_sec = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(seconds=1)

    if cron_expression:
        if start_time and start_time > now_plus_1_sec:
            base = start_time
        else:
            base = now_plus_1_sec

        next_occurrence = next_occurrence_for_cron(
            expression=cron_expression,
            base=base,
        )
    elif start_time and interval:
        if start_time > now_plus_1_sec:
            next_occurrence = start_time
        else:
            next_occurrence = next_occurrence_for_interval(
                interval=interval,
                start=start_time,
                base=now_plus_1_sec,
            )
    elif run_once_start_time:
        next_occurrence = run_once_start_time
    else:
        return None

    return next_occurrence
