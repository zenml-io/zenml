import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from zenml.models.v2.core.schedule import ScheduleRequest, ScheduleUpdate


def test_schedule_request_object_validations():
    ScheduleRequest(
        project=uuid.uuid4(),
        name="daily schedule",
        cron_expression="* * * * *",
        active=True,
        orchestrator_id=uuid.uuid4(),
        pipeline_id=uuid.uuid4(),
    )

    # check cron validity

    with pytest.raises(ValidationError):
        ScheduleRequest(
            project=uuid.uuid4(),
            name="daily schedule",
            cron_expression="60 * * * *",
            active=True,
            orchestrator_id=uuid.uuid4(),
            pipeline_id=uuid.uuid4(),
        )

    # check missing schedule options

    with pytest.raises(ValidationError):
        ScheduleRequest(
            project=uuid.uuid4(),
            name="daily schedule",
            active=True,
            orchestrator_id=uuid.uuid4(),
            pipeline_id=uuid.uuid4(),
            start_time=datetime.now(tz=timezone.utc),
        )

    # check datetime utc conversions

    schedule = ScheduleRequest(
        interval_second=timedelta(minutes=60),
        project=uuid.uuid4(),
        name="daily schedule",
        active=True,
        orchestrator_id=uuid.uuid4(),
        pipeline_id=uuid.uuid4(),
        start_time=datetime(
            year=2025,
            month=1,
            day=1,
            hour=12,
            minute=0,
            tzinfo=ZoneInfo("Europe/Berlin"),
        ),
        end_time=datetime(
            year=2025,
            month=1,
            day=10,
            hour=12,
            minute=0,
            tzinfo=ZoneInfo("Europe/Berlin"),
        ),
    )

    assert schedule.start_time.hour == 11
    assert schedule.end_time.hour == 11
    assert schedule.start_time.tzinfo is None
    assert schedule.end_time.tzinfo is None


def test_schedule_update_object_validations():
    ScheduleUpdate(
        name="daily schedule",
        cron_expression="* * * * *",
    )

    # check cron validity

    with pytest.raises(ValidationError):
        ScheduleUpdate(
            name="daily schedule",
            cron_expression="60 * * * *",
        )
