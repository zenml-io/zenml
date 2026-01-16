import uuid

import pytest

from zenml import pipeline, step
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ScheduleRequest,
    ScheduleUpdate,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def create_requirements():
    pass


@step(name=f"test_step_{str(uuid.uuid4())[:8]}")
def test_step():
    print("OK!")


@pipeline(name=f"test_pipeline_{str(uuid.uuid4())[:8]}")
def test_pipeline():
    _ = test_step()


def test_crud_cycle():
    client = Client()

    run = test_pipeline()

    # create schedule

    schedule = client.zen_store.create_schedule(
        schedule=ScheduleRequest(
            name=f"daily_schedule_{str(uuid.uuid4())[:8]}",
            cron_expression="0 0 * * *",
            orchestrator_id=run.stack.components[
                StackComponentType.ORCHESTRATOR
            ][0].id,
            active=True,
            pipeline_id=run.pipeline.id,
            project=run.project_id,
        )
    )

    # get by key

    s = client.get_schedule(name_id_or_prefix=schedule.id)

    assert s.name == schedule.name
    assert s.cron_expression == schedule.cron_expression

    # update

    client.zen_store.update_schedule(
        schedule_id=schedule.id,
        schedule_update=ScheduleUpdate(cron_expression="0 1 * * *"),
    )

    s = client.get_schedule(name_id_or_prefix=schedule.id)

    assert s.name == schedule.name
    assert s.cron_expression == "0 1 * * *"

    client.zen_store.delete_schedule(schedule_id=schedule.id, soft=True)

    assert client.get_schedule(name_id_or_prefix=schedule.id).is_archived

    if isinstance(client.zen_store, SqlZenStore):
        with pytest.raises(IllegalOperationError):
            client.zen_store.update_schedule(
                schedule_id=schedule.id,
                schedule_update=ScheduleUpdate(cron_expression="0 1 * * *"),
            )

    assert (
        client.list_schedules(is_archived=False, name=schedule.name).total == 0
    )
    assert (
        client.list_schedules(is_archived=True, name=schedule.name).total == 1
    )

    client.zen_store.delete_schedule(schedule_id=schedule.id, soft=False)

    with pytest.raises(KeyError):
        client.get_schedule(name_id_or_prefix=schedule.id)
