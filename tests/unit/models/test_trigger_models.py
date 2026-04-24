from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.enums import (
    SourceType,
    TriggerFlavor,
    TriggerRunConcurrency,
    TriggerType,
)
from zenml.models import (
    PlatformEventTriggerRequest,
    PlatformEventTriggerResponseBody,
    PlatformEventTriggerUpdate,
    ScheduleTriggerRequest,
    ScheduleTriggerResponseBody,
    ScheduleTriggerUpdate,
)


def test_schedule_trigger_valid_and_inheritance():
    end_time = datetime(2026, 1, 1, 12, 0)
    req = ScheduleTriggerRequest(
        project=uuid4(),
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        concurrency=TriggerRunConcurrency.SKIP,
        cron_expression="0 * * * *",
        end_time=end_time,
        max_runs=10,
    )
    assert req.name == "sched"
    assert req.type == TriggerType.SCHEDULE
    assert req.flavor == TriggerFlavor.NATIVE_SCHEDULE
    assert req.end_time == end_time
    assert req.max_runs == 10

    upd = ScheduleTriggerUpdate(
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        cron_expression="0 * * * *",
        end_time=end_time,
        max_runs=5,
    )
    assert upd.name == "sched"
    assert upd.type == TriggerType.SCHEDULE
    assert upd.end_time == end_time
    assert upd.max_runs == 5

    body = ScheduleTriggerResponseBody(
        project_id=uuid4(),
        user_id=uuid4(),
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        concurrency=TriggerRunConcurrency.SKIP,
        is_archived=False,
        cron_expression="0 * * * *",
        end_time=end_time,
        max_runs=3,
        next_occurrence=datetime(2026, 1, 1, 12, 0),
    )
    assert body.name == "sched"
    assert body.next_occurrence is not None
    assert body.end_time == end_time
    assert body.max_runs == 3


def test_schedule_trigger_validators():
    # no scheduling option
    with pytest.raises(ValidationError):
        ScheduleTriggerRequest(
            project=uuid4(),
            name="sched",
            active=True,
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            cron_expression=None,
            interval=None,
            run_once_start_time=None,
        )

    # multiple options
    with pytest.raises(ValidationError):
        ScheduleTriggerRequest(
            project=uuid4(),
            name="sched",
            active=True,
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            cron_expression="0 * * * *",
            interval=60,
            start_time=datetime.utcnow(),
        )

    # interval without start_time
    with pytest.raises(ValidationError):
        ScheduleTriggerRequest(
            project=uuid4(),
            name="sched",
            active=True,
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            cron_expression=None,
            interval=60,
        )

    # invalid time boundaries
    with pytest.raises(ValidationError):
        ScheduleTriggerRequest(
            project=uuid4(),
            name="sched",
            active=True,
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            cron_expression="0 * * * *",
            start_time=datetime(2026, 1, 2),
            end_time=datetime(2026, 1, 1),
        )


def test_schedule_trigger_timezone_normalization():
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))

    req = ScheduleTriggerRequest(
        project=uuid4(),
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        cron_expression="0 * * * *",
        start_time=dt,
    )

    assert req.start_time.tzinfo is None
    assert req.start_time == datetime(2026, 1, 1, 10, 0)

    end_time = datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))
    req_with_end_time = ScheduleTriggerRequest(
        project=uuid4(),
        name="sched-with-end-time",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        cron_expression="0 * * * *",
        end_time=end_time,
    )
    assert req_with_end_time.end_time is not None
    assert req_with_end_time.end_time.tzinfo is None
    assert req_with_end_time.end_time == datetime(2026, 1, 1, 10, 0)


def test_schedule_trigger_response_next_occurrence_behavior():
    active = ScheduleTriggerResponseBody(
        project_id=uuid4(),
        user_id=uuid4(),
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        concurrency=TriggerRunConcurrency.SKIP,
        is_archived=False,
        cron_expression="0 * * * *",
        next_occurrence=datetime(2026, 1, 1, 12, 0),
    )
    assert active.next_occurrence is not None

    inactive = ScheduleTriggerResponseBody(
        project_id=uuid4(),
        user_id=uuid4(),
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        name="sched",
        active=False,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        concurrency=TriggerRunConcurrency.SKIP,
        is_archived=False,
        cron_expression="0 * * * *",
        next_occurrence=datetime(2026, 1, 1, 12, 0),
    )
    assert inactive.next_occurrence is None

    archived = ScheduleTriggerResponseBody(
        project_id=uuid4(),
        user_id=uuid4(),
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        concurrency=TriggerRunConcurrency.SKIP,
        is_archived=True,
        cron_expression="0 * * * *",
        next_occurrence=datetime(2026, 1, 1, 12, 0),
    )
    assert archived.next_occurrence is None


def test_platform_event_valid_and_inheritance():
    end_time = datetime(2026, 2, 1, 12, 0)
    req = PlatformEventTriggerRequest(
        project=uuid4(),
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
        target_events=["completed"],
        end_time=end_time,
        max_runs=9,
    )
    assert req.name == "evt"
    assert req.source_entity.type == SourceType.PIPELINE_RUN
    assert req.end_time == end_time
    assert req.max_runs == 9

    upd = PlatformEventTriggerUpdate(
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
        target_events=["completed"],
        end_time=end_time,
        max_runs=4,
    )
    assert upd.source_entity.type == SourceType.PIPELINE_RUN
    assert upd.end_time == end_time
    assert upd.max_runs == 4

    body = PlatformEventTriggerResponseBody(
        project_id=uuid4(),
        user_id=uuid4(),
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        concurrency=TriggerRunConcurrency.SKIP,
        is_archived=False,
        source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
        target_events=["completed"],
        end_time=end_time,
        max_runs=2,
    )
    assert body.source_entity.type == SourceType.PIPELINE_RUN
    assert body.end_time == end_time
    assert body.max_runs == 2


def test_platform_event_shared_stop_criteria_validations_and_payload():
    with pytest.raises(ValidationError):
        PlatformEventTriggerRequest(
            project=uuid4(),
            name="evt",
            active=True,
            type=TriggerType.PLATFORM_EVENT,
            flavor=TriggerFlavor.PLATFORM_EVENT,
            source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
            target_events=["completed"],
            max_runs=0,
        )

    req = PlatformEventTriggerRequest(
        project=uuid4(),
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
        target_events=["completed"],
        end_time=datetime(
            2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2))
        ),
        max_runs=2,
    )
    assert req.end_time is not None
    assert req.end_time.tzinfo is None
    assert req.end_time == datetime(2026, 1, 1, 10, 0)


def test_platform_event_invalid_combinations():
    # invalid: pipeline + COMPLETED
    with pytest.raises(ValidationError):
        PlatformEventTriggerRequest(
            project=uuid4(),
            name="evt",
            active=True,
            type=TriggerType.PLATFORM_EVENT,
            flavor=TriggerFlavor.PLATFORM_EVENT,
            source_entity={"type": SourceType.PIPELINE, "id": uuid4()},
            target_events=["completed"],
        )

    # invalid: pipeline_run + RUN_COMPLETED
    with pytest.raises(ValidationError):
        PlatformEventTriggerRequest(
            project=uuid4(),
            name="evt",
            active=True,
            type=TriggerType.PLATFORM_EVENT,
            flavor=TriggerFlavor.PLATFORM_EVENT,
            source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
            target_events=["run_completed"],
        )
