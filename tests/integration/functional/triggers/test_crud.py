import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.integration.functional.utils import sample_name
from zenml import (
    PlatformEventTriggerRequest,
    PlatformEventTriggerResponse,
    PlatformEventTriggerUpdate,
)
from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import (
    ExecutionStatus,
    LogicalOperators,
    TriggerFlavor,
    TriggerType,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    PipelineBuildRequest,
    PipelineRequest,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    ScheduleTriggerRequest,
    ScheduleTriggerUpdate,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _create_runnable_snapshot(
    client: Client, pipeline_id: uuid.UUID
) -> PipelineSnapshotResponse:
    project_id = client.active_project.id
    build = client.zen_store.create_build(
        PipelineBuildRequest(
            project=project_id,
            pipeline=pipeline_id,
            stack=client.active_stack.id,
            images={},
            is_local=False,
            contains_code=True,
        )
    )
    return client.zen_store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            run_name_template=sample_name("trigger-filter-snapshot"),
            pipeline_configuration=PipelineConfiguration(
                name=sample_name("trigger-filter-config")
            ),
            pipeline=pipeline_id,
            stack=client.active_stack.id,
            build=build.id,
            client_version="0.1.0",
            server_version="0.1.0",
            is_dynamic=False,
        )
    )


def test_schedule_crud_happy_path(clean_client):
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


def test_event_crud_happy_path(clean_client):
    from zenml.enums import PipelineEvent, SourceType, TriggerRunConcurrency
    from zenml.models import SourceEntity

    project = clean_client.active_project
    store = clean_client.zen_store

    pipeline_model = store.create_pipeline(
        PipelineRequest(
            name=sample_name("trigger-test-pipeline"),
            project=project.id,
        )
    )

    trigger = PlatformEventTriggerRequest(
        name=sample_name("platform-test-trigger"),
        source_entity=SourceEntity(
            type=SourceType.PIPELINE,
            id=pipeline_model.id,
        ),
        target_events=[PipelineEvent.RUN_COMPLETED],
        concurrency=TriggerRunConcurrency.SUBMIT,
        project=project.id,
    )

    trigger_response = store.create_trigger(trigger)

    assert not trigger_response.is_archived
    assert isinstance(trigger_response, PlatformEventTriggerResponse)

    get_response = store.get_trigger(trigger_response.id)

    assert trigger_response.model_dump() == get_response.model_dump()

    update = PlatformEventTriggerUpdate(
        name=get_response.name,
        source_entity=SourceEntity(
            type=SourceType.PIPELINE,
            id=pipeline_model.id,
        ),
        target_events=[
            PipelineEvent.RUN_COMPLETED,
            PipelineEvent.RUN_FAILED,
        ],
        concurrency=TriggerRunConcurrency.SUBMIT,
    )

    updated_response = store.update_trigger(
        trigger_id=trigger_response.id,
        trigger_update=update,
    )

    assert updated_response.target_events == update.target_events

    store.delete_trigger(trigger_response.id, soft=True)

    get_response = store.get_trigger(trigger_response.id)

    assert get_response.is_archived


def test_snapshot_associations(clean_client):
    # TODO: update test case with a runnable mock snapshot
    pytest.skip("Temporarily skipping check due to flakiness.")
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


def test_list_schedule_triggers_filters_by_pipeline_and_snapshot(clean_client):
    project_id = clean_client.active_project.id
    store = clean_client.zen_store

    first_pipeline = store.create_pipeline(
        PipelineRequest(
            name=sample_name("trigger-filter-pipeline"),
            project=project_id,
        )
    )
    second_pipeline = store.create_pipeline(
        PipelineRequest(
            name=sample_name("trigger-filter-pipeline"),
            project=project_id,
        )
    )
    snapshots = [
        _create_runnable_snapshot(clean_client, first_pipeline.id),
        _create_runnable_snapshot(clean_client, first_pipeline.id),
        _create_runnable_snapshot(clean_client, second_pipeline.id),
    ]
    triggers = [
        clean_client.create_schedule_trigger(
            name=sample_name("trigger-filter"),
            cron_expression="* * * * *",
        )
        for _ in snapshots
    ]
    for trigger, snapshot in zip(triggers, snapshots):
        store.attach_trigger_to_snapshot(
            trigger_id=trigger.id,
            snapshot_id=snapshot.id,
        )

    pipeline_triggers = clean_client.list_schedule_triggers(
        pipeline_id=str(first_pipeline.id)
    )
    snapshot_triggers = clean_client.list_schedule_triggers(
        snapshot_id=str(snapshots[0].id)
    )

    assert {trigger.id for trigger in pipeline_triggers.items} == {
        triggers[0].id,
        triggers[1].id,
    }
    assert {trigger.id for trigger in snapshot_triggers.items} == {
        triggers[0].id
    }


def test_run_associations(clean_client):
    # TODO: update test case with a runnable mock snapshot
    pytest.skip("Temporarily skipping check due to flakiness.")

    if not isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Trigger Execution assoc testing requires SqlZenStore")

    # create placeholders

    project = clean_client.active_project
    store: SqlZenStore = clean_client.zen_store

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

    cron_trigger = store.create_trigger(
        ScheduleTriggerRequest(
            project=project.id,
            name=sample_name("trigger-test", random_factor=6),
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            active=True,
            cron_expression="* 1 * * *",
        )
    )

    interval_trigger = store.create_trigger(
        ScheduleTriggerRequest(
            project=project.id,
            name=sample_name("trigger-test", random_factor=6),
            type=TriggerType.SCHEDULE,
            flavor=TriggerFlavor.NATIVE_SCHEDULE,
            active=True,
            interval=600,
            start_time=datetime.now(tz=timezone.utc),
        )
    )

    clean_client.attach_trigger_to_snapshot(
        trigger_id=cron_trigger.id, pipeline_snapshot_id=snapshot.id
    )

    clean_client.attach_trigger_to_snapshot(
        trigger_id=interval_trigger.id, pipeline_snapshot_id=snapshot.id
    )

    # test run that has no trigger attached

    run1, _ = store.get_or_create_run(
        pipeline_run=PipelineRunRequest(
            project=project.id,
            snapshot=snapshot.id,
            name=sample_name("trigger-test-run"),
            status=ExecutionStatus.RUNNING,
        )
    )

    assert run1.trigger is None

    store.create_trigger_execution(
        trigger_id=cron_trigger.id,
        pipeline_run_id=run1.id,
    )

    run1 = store.get_run(run1.id)

    assert run1.trigger.id == cron_trigger.id

    run2, _ = store.get_or_create_run(
        pipeline_run=PipelineRunRequest(
            project=project.id,
            snapshot=snapshot.id,
            name=sample_name("trigger-test-run"),
            status=ExecutionStatus.RUNNING,
        )
    )

    store.create_trigger_execution(
        trigger_id=interval_trigger.id,
        pipeline_run_id=run2.id,
    )

    run2 = store.get_run(run2.id)

    assert run2.trigger.id == interval_trigger.id

    runs = store.list_runs(
        runs_filter_model=PipelineRunFilter(trigger_id=uuid.uuid4())
    )

    assert len(runs.items) == 0

    runs = store.list_runs(
        runs_filter_model=PipelineRunFilter(
            trigger_id=cron_trigger.id,
        )
    )

    assert len(runs.items) == 1
    assert runs.items[0].trigger.id == cron_trigger.id

    cron_trigger = store.get_trigger(
        trigger_id=cron_trigger.id,
    )

    assert cron_trigger.latest_run.id == run1.id

    run3, _ = store.get_or_create_run(
        pipeline_run=PipelineRunRequest(
            project=project.id,
            snapshot=snapshot.id,
            name=sample_name("trigger-test-run"),
            status=ExecutionStatus.RUNNING,
        )
    )

    store.create_trigger_execution(
        trigger_id=cron_trigger.id,
        pipeline_run_id=run3.id,
    )

    assert (
        store.get_trigger(trigger_id=cron_trigger.id).latest_run.id == run3.id
    )


def test_sdk_utilities(clean_client):
    created = clean_client.create_schedule_trigger(
        name=sample_name("trigger-test"),
        active=True,
        cron_expression="* 1 * * *",
    )

    print(created)

    assert created.type == TriggerType.SCHEDULE
    assert created.next_occurrence is not None
    assert not created.is_archived

    updated = clean_client.update_schedule_trigger(
        trigger_name_id_or_prefix=created.id, cron_expression="* 2 * * *"
    )

    assert updated.type == TriggerType.SCHEDULE
    assert updated.name == created.name
    assert updated.cron_expression == "* 2 * * *"
    assert not updated.is_archived

    got = clean_client.get_schedule_trigger(created.id)

    assert got.cron_expression == "* 2 * * *"

    assert clean_client.get_schedule_trigger(created.name).id == created.id
    assert (
        clean_client.get_schedule_trigger(created.name[:10]).id == created.id
    )
    assert (
        clean_client.get_schedule_trigger(str(created.id)[:8]).id == created.id
    )

    listed = clean_client.list_schedule_triggers()
    assert created.id in {trigger.id for trigger in listed.items}

    listed_by_name = clean_client.list_schedule_triggers(name=created.name)
    assert listed_by_name.total == 1
    assert listed_by_name.items[0].id == created.id

    listed_by_id_prefix = clean_client.list_schedule_triggers(
        id=f"startswith:{str(created.id)[:8]}"
    )
    assert created.id in {trigger.id for trigger in listed_by_id_prefix.items}

    listed_by_active_status = clean_client.list_schedule_triggers(active=True)
    assert created.id in {
        trigger.id for trigger in listed_by_active_status.items
    }

    listed_by_missing_name = clean_client.list_schedule_triggers(
        name="definitely-missing-trigger"
    )
    assert created.id not in {
        trigger.id for trigger in listed_by_missing_name.items
    }

    inactive = clean_client.create_schedule_trigger(
        name=sample_name("inactive-trigger-test"),
        active=False,
        cron_expression="* 3 * * *",
    )

    listed_by_and_filters = clean_client.list_schedule_triggers(
        logical_operator=LogicalOperators.AND,
        name=created.name,
        active=True,
    )
    assert listed_by_and_filters.total == 1
    assert listed_by_and_filters.items[0].id == created.id

    listed_by_or_filters = clean_client.list_schedule_triggers(
        logical_operator=LogicalOperators.OR,
        name="definitely-missing-trigger",
        active=True,
    )
    or_filter_ids = {trigger.id for trigger in listed_by_or_filters.items}
    assert created.id in or_filter_ids
    assert inactive.id not in or_filter_ids

    with pytest.raises(KeyError):
        clean_client.get_schedule_trigger("definitely-missing-trigger")

    clean_client.delete_trigger(created.id)
    clean_client.delete_trigger(inactive.id)

    with pytest.raises(KeyError):
        got = clean_client.get_schedule_trigger(created.id)
        assert got.is_archived
