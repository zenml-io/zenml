import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.integration.functional.utils import sample_name
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import TriggerFlavor, TriggerType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    PipelineRequest,
    PipelineSnapshotRequest,
    ScheduleTriggerRequest,
    ScheduleTriggerUpdate,
)


def test_crud_happy_path(clean_client):
    project = clean_client.active_project
    store = clean_client.zen_store

    time_of_launch = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
    time_of_launch = time_of_launch.replace(tzinfo=None, microsecond=0)

    # create trigger

    trigger = ScheduleTriggerRequest(
        project=project.id,
        name=sample_name("trigger-test", random_factor=6),
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        start_time=time_of_launch,
        interval=60,
        end_time=time_of_launch + timedelta(minutes=10),
        active=True,
    )

    assert trigger.get_extra_fields()["next_occurrence"] == time_of_launch

    assert isinstance(trigger.get_config(), str)

    trigger_response = store.create_trigger(trigger)

    # check populated fields

    assert not trigger_response.is_archived
    assert trigger_response.next_occurrence == time_of_launch

    # retrieve trigger

    t = store.get_trigger(trigger_response.id)

    assert t.project_id == project.id

    # update trigger

    new_name = sample_name("update-trigger-test", random_factor=6)

    update_response = store.update_trigger(
        trigger_id=trigger_response.id,
        trigger_update=ScheduleTriggerUpdate(
            cron_expression="* 1 * * *",
            interval=None,
            name=new_name,
            active=True,
            start_time=time_of_launch,
        ),
    )

    new_response = store.get_trigger(update_response.id)

    for updated_trigger in [new_response, update_response]:
        assert updated_trigger.name == new_name
        assert updated_trigger.start_time == time_of_launch
        assert updated_trigger.cron_expression == "* 1 * * *"
        assert updated_trigger.interval is None
        assert (
            updated_trigger.next_occurrence != t.next_occurrence
        )  # next occurrence has been updated


def test_associations(clean_client):
    project = clean_client.active_project
    store = clean_client.zen_store

    # create placeholder objects

    pipeline_model = store.create_pipeline(
        PipelineRequest(
            name=sample_name("trigger-test-pipeline"),
            project=project.id,
        )
    )

    step_name = sample_name("trigger-test-step")

    snapshot = store.create_snapshot(
        PipelineSnapshotRequest(
            project=project.id,
            run_name_template=sample_name("trigger-test-snap"),
            pipeline_configuration=PipelineConfiguration(
                name=sample_name("foo")
            ),
            stack=clean_client.active_stack.id,
            pipeline=pipeline_model.id,
            client_version="0.1.0",
            server_version="0.1.0",
            step_configurations={
                step_name: Step(
                    spec=StepSpec(
                        source=Source(
                            module="acme.foo",
                            type=SourceType.INTERNAL,
                        ),
                        upstream_steps=[],
                        invocation_id=str(uuid.uuid4()),
                    ),
                    config=StepConfiguration(name=step_name),
                    step_config_overrides=StepConfiguration(name=step_name),
                )
            },
            is_dynamic=False,
        )
    )

    trigger_response = store.create_trigger(
        ScheduleTriggerRequest(
            project=project.id,
            name=sample_name("trigger-test", random_factor=6),
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            active=True,
            cron_expression="* 1 * * *",
        )
    )

    assert trigger_response.snapshots == []

    # test trigger-snapshot attachment

    store.attach_trigger_to_snapshot(
        trigger_id=trigger_response.id,
        snapshot_id=snapshot.id,
    )

    trigger_response = store.get_trigger(trigger_response.id)
    snapshot = store.get_snapshot(snapshot.id)

    assert trigger_response.snapshots[0].id == snapshot.id

    # test trigger-snapshot detachment

    store.detach_trigger_from_snapshot(
        trigger_id=trigger_response.id,
        snapshot_id=snapshot.id,
    )

    trigger_response = store.get_trigger(trigger_response.id)
    snapshot = store.get_snapshot(snapshot.id)

    assert trigger_response.snapshots == []

    store.update_trigger(
        trigger_id=trigger_response.id,
        trigger_update=ScheduleTriggerUpdate(
            active=False,
            name=trigger_response.name,
            cron_expression=trigger_response.cron_expression,
        ),
    )

    # re-attach and test archival flow

    store.attach_trigger_to_snapshot(
        trigger_id=trigger_response.id,
        snapshot_id=snapshot.id,
    )

    store.delete_trigger(trigger_response.id, soft=True)

    trigger_response = store.get_trigger(trigger_response.id)
    assert trigger_response.is_archived

    snapshot = store.get_snapshot(
        snapshot.id
    )  # test archival detaches associations

    with pytest.raises(IllegalOperationError):
        store.attach_trigger_to_snapshot(
            trigger_id=trigger_response.id,
            snapshot_id=snapshot.id,
        )


def test_sdk_utilities(clean_client):
    created = clean_client.create_schedule_trigger(
        name=sample_name("trigger-test"),
        active=True,
        cron_expression="* 1 * * *",
    )

    assert created.type == TriggerType.SCHEDULE
    assert created.next_occurrence is not None
    assert not created.is_archived

    updated = clean_client.update_schedule_trigger(
        trigger_id=created.id, cron_expression="* 2 * * *"
    )

    assert updated.type == TriggerType.SCHEDULE
    assert updated.name == created.name
    assert updated.cron_expression == "* 2 * * *"
    assert not updated.is_archived

    got = clean_client.get_schedule_trigger(created.id)

    assert got.cron_expression == "* 2 * * *"

    clean_client.delete_trigger(created.id)

    got = clean_client.get_schedule_trigger(created.id)
    assert got.is_archived
