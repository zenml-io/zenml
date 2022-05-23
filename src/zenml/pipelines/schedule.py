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

import datetime
from typing import Optional

from pydantic import BaseModel


class Schedule(BaseModel):
    """Class for defining a pipeline schedule.

    Attributes:
        start_time: Datetime object to indicate when to start the schedule.
        end_time: Datetime object to indicate when to end the schedule.
        interval_second: Datetime timedelta indicating the seconds between two
            recurring runs for a periodic schedule.
        catchup: Whether the recurring run should catch up if behind schedule.
            For example, if the recurring run is paused for a while and
            re-enabled afterwards. If catchup=True, the scheduler will catch
            up on (backfill) each missed interval. Otherwise, it only
            schedules the latest interval if more than one interval is ready to
            be scheduled. Usually, if your pipeline handles backfill
            internally, you should turn catchup off to avoid duplicate backfill.
    """

    start_time: datetime.datetime
    end_time: Optional[datetime.datetime] = None
    interval_second: datetime.timedelta
    catchup: bool = False

    @property
    def utc_start_time(self) -> str:
        """ISO-formatted string of the UTC start time."""
        return self.start_time.astimezone(datetime.timezone.utc).isoformat()

    @property
    def utc_end_time(self) -> Optional[str]:
        """Optional ISO-formatted string of the UTC end time."""
        if not self.end_time:
            return None

        return self.end_time.astimezone(datetime.timezone.utc).isoformat()
