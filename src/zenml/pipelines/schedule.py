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

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Schedule(BaseModel):
    """Class that let's user define a schedule for a pipeline.

    Attributes:
        start_time: Datetime object to indicate when to start the schedule.
        end_time: Datetime object to indicate when to start the schedule.
        interval_second: Integer indicating the seconds between two recurring runs in for a periodic schedule.
        catchup: Whether the recurring run should catch up if behind schedule. For example, if the recurring run is
        paused for a while and re-enabled afterwards. If catchup=True, the scheduler will catch up on (backfill)
        each missed interval. Otherwise, it only schedules the latest interval if more than one interval is ready to
        be scheduled. Usually, if your pipeline handles backfill internally, you should turn catchup off to avoid
        duplicate backfill.
        cron_expression: A cron expression representing a set of times, using 6 space-separated fields,
        e.g. “0 0 9 ? * 2-6”. See [here](https://pkg.go.dev/github.com/robfig/cron#hdr-CRON_Expression_Format)
        for details of the cron expression format.
    """

    start_time: datetime
    end_time: Optional[datetime] = None
    interval_second: int
    catchup: bool = False
    cron_expression: Optional[str] = None
