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
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from zenml.pipelines import Schedule


def test_schedule_requires_cron_or_interval():
    """Tests that a schedule can only be created if it contains a cron expression and/or an interval."""
    with does_not_raise():
        # just a cron expression
        Schedule(cron_expression="* * * * *")
        # interval specified by start time + interval duration
        Schedule(
            start_time=datetime.datetime.now(),
            interval_second=datetime.timedelta(seconds=5),
        )
        # both is also fine but cron will take precedence
        Schedule(
            cron_expression="* * * * *",
            start_time=datetime.datetime.now(),
            interval_second=datetime.timedelta(seconds=5),
        )
        # run once start time
        Schedule(run_once_start_time=datetime.datetime.now())

    with pytest.raises(ValidationError):
        # no cron and no periodic
        Schedule()
