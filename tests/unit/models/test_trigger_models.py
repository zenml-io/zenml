import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    GitHubWebhookConfiguration,
    GitHubWebhookEvent,
    MergedPullRequest,
    PlatformEventTriggerRequest,
    PlatformEventTriggerResponse,
    PlatformEventTriggerResponseBody,
    PlatformEventTriggerUpdate,
    PushEvent,
    ReleasePublished,
    ScheduleTriggerRequest,
    ScheduleTriggerResponseBody,
    ScheduleTriggerUpdate,
    TriggerDispatchStatusCode,
    TriggerExecutionInfo,
    TriggerResponseResources,
    TriggerSnapshotDispatchState,
    WebhookTriggerRequest,
    WebhookTriggerUpdate,
    WorkflowRunCompleted,
)


def test_trigger_execution_info_defaults_pipeline_lineage() -> None:
    """Legacy trigger execution payloads should get an empty lineage."""
    upstream_run_id = uuid4()

    info = TriggerExecutionInfo.model_validate(
        {"upstream_run_id": str(upstream_run_id)}
    )

    assert info.upstream_run_id == upstream_run_id
    assert info.upstream_pipeline_ids == []
    assert "upstream_pipeline_ids" in info.model_dump()


def test_webhook_trigger_update_requires_complete_payload() -> None:
    """Webhook trigger updates preserve PUT semantics."""
    with pytest.raises(
        ValidationError, match="must include all mutable fields"
    ):
        WebhookTriggerUpdate(name="webhook-trigger")

    detached = WebhookTriggerUpdate(
        name="webhook-trigger",
        active=False,
        concurrency=TriggerRunConcurrency.SKIP,
        webhook_integration_id=None,
    )
    integration_id = uuid4()
    attached = WebhookTriggerUpdate(
        name="webhook-trigger",
        active=True,
        concurrency=TriggerRunConcurrency.SUBMIT,
        webhook_integration_id=integration_id,
    )

    assert detached.get_extra_fields() == {"webhook_integration_id": None}
    assert attached.get_extra_fields() == {
        "webhook_integration_id": integration_id
    }


def test_github_webhook_trigger_serializes_typed_event_configuration() -> None:
    """Multiple typed GitHub event configurations are stored in config JSON."""
    events = [
        MergedPullRequest(
            repo='oneof:["zenml-io/zenml", "zenml-io/zenml-pro"]',
            target_branch="develop",
            source_branch="startswith:feature/",
            author="george",
        ),
        PushEvent(repo="zenml-io/zenml", branch="main", actor="george"),
        ReleasePublished(
            repo="zenml-io/zenml",
            tag="startswith:v",
            target_branch="main",
        ),
        WorkflowRunCompleted(
            workflow="CI",
            conclusion='oneof:["success", "failure"]',
            actor="george",
        ),
    ]
    request = WebhookTriggerRequest(
        project=uuid4(),
        name="github-webhook-trigger",
        flavor=TriggerFlavor.GITHUB_WEBHOOK,
        webhook_integration_id=uuid4(),
        events=events,
    )

    assert events[0].type == GitHubWebhookEvent.MERGED_PULL_REQUEST
    assert json.loads(request.get_config()) == {
        "events": [
            {
                "type": "merged_pull_request",
                "repo": 'oneof:["zenml-io/zenml", "zenml-io/zenml-pro"]',
                "target_branch": "develop",
                "source_branch": "startswith:feature/",
                "author": "george",
            },
            {
                "type": "push",
                "repo": "zenml-io/zenml",
                "branch": "main",
                "actor": "george",
            },
            {
                "type": "release_published",
                "repo": "zenml-io/zenml",
                "tag": "startswith:v",
                "target_branch": "main",
            },
            {
                "type": "workflow_run_completed",
                "workflow": "CI",
                "conclusion": 'oneof:["success", "failure"]',
                "actor": "george",
            },
        ]
    }


def test_webhook_trigger_event_configuration_matches_flavor() -> None:
    """GitHub requires event configuration while custom forbids it."""
    events = [MergedPullRequest(repo="zenml-io/zenml")]

    with pytest.raises(ValidationError, match="require event configurations"):
        WebhookTriggerRequest(
            project=uuid4(),
            name="github-webhook-trigger",
            flavor=TriggerFlavor.GITHUB_WEBHOOK,
        )

    with pytest.raises(ValidationError, match="do not support"):
        WebhookTriggerRequest(
            project=uuid4(),
            name="custom-webhook-trigger",
            flavor=TriggerFlavor.CUSTOM_WEBHOOK,
            events=events,
        )


def test_github_webhook_configuration_loads_yaml(tmp_path: Path) -> None:
    """The CLI configuration wrapper loads heterogeneous event lists."""
    path = tmp_path / "events.yaml"
    path.write_text(
        """
events:
  - type: merged_pull_request
    repo: zenml-io/zenml
    target_branch: develop
  - type: push
    repo: zenml-io/zenml
    branch: main
""".lstrip()
    )

    configuration = GitHubWebhookConfiguration.from_yaml(str(path))

    assert configuration.events == [
        MergedPullRequest(repo="zenml-io/zenml", target_branch="develop"),
        PushEvent(repo="zenml-io/zenml", branch="main"),
    ]


def test_github_webhook_configuration_rejects_empty_event_list() -> None:
    """GitHub configuration must select at least one event."""
    with pytest.raises(ValidationError):
        GitHubWebhookConfiguration(events=[])


@pytest.mark.parametrize(
    "field, value",
    [
        ("repo", "startswith:zenml-io/"),
        ("author", "contains:george"),
        ("source_branch", "oneof:not-json"),
        ("target_branch", 'oneof:["develop", 42]'),
    ],
)
def test_pull_request_merged_rejects_unsupported_filters(
    field: str, value: str
) -> None:
    """Semantic event fields enforce their operator allowlists."""
    with pytest.raises(ValidationError):
        MergedPullRequest(**{field: value})


def test_schedule_trigger_valid_and_inheritance():
    req = ScheduleTriggerRequest(
        project=uuid4(),
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        concurrency=TriggerRunConcurrency.SKIP,
        cron_expression="0 * * * *",
    )
    assert req.name == "sched"
    assert req.type == TriggerType.SCHEDULE
    assert req.flavor == TriggerFlavor.NATIVE_SCHEDULE

    upd = ScheduleTriggerUpdate(
        name="sched",
        active=True,
        type=TriggerType.SCHEDULE,
        flavor=TriggerFlavor.NATIVE_SCHEDULE,
        cron_expression="0 * * * *",
    )
    assert upd.name == "sched"
    assert upd.type == TriggerType.SCHEDULE

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
        next_occurrence=datetime(2026, 1, 1, 12, 0),
    )
    assert body.name == "sched"
    assert body.next_occurrence is not None


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
    req = PlatformEventTriggerRequest(
        project=uuid4(),
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
        target_events=["completed"],
    )
    assert req.name == "evt"
    assert req.source_entity.type == SourceType.PIPELINE_RUN

    upd = PlatformEventTriggerUpdate(
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        source_entity={"type": SourceType.PIPELINE_RUN, "id": uuid4()},
        target_events=["completed"],
    )
    assert upd.source_entity.type == SourceType.PIPELINE_RUN

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
    )
    assert body.source_entity.type == SourceType.PIPELINE_RUN

    snapshot_id = uuid4()
    dispatch_state = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.SKIPPED_TRIGGER_CYCLE,
        last_status_details={"cycle_pipeline_ids": [uuid4(), uuid4()]},
    )
    response = PlatformEventTriggerResponse(
        id=uuid4(),
        body=body,
        resources=TriggerResponseResources(
            snapshot_dispatch_states={snapshot_id: dispatch_state}
        ),
    )

    assert response.snapshot_dispatch_states == {snapshot_id: dispatch_state}


def test_platform_event_snapshot_source_valid():
    req = PlatformEventTriggerRequest(
        project=uuid4(),
        name="evt",
        active=True,
        type=TriggerType.PLATFORM_EVENT,
        flavor=TriggerFlavor.PLATFORM_EVENT,
        source_entity={"type": SourceType.PIPELINE_SNAPSHOT, "id": uuid4()},
        target_events=["run_completed"],
    )

    assert req.source_entity.type == SourceType.PIPELINE_SNAPSHOT


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

    # invalid: pipeline_snapshot + COMPLETED
    with pytest.raises(ValidationError):
        PlatformEventTriggerRequest(
            project=uuid4(),
            name="evt",
            active=True,
            type=TriggerType.PLATFORM_EVENT,
            flavor=TriggerFlavor.PLATFORM_EVENT,
            source_entity={
                "type": SourceType.PIPELINE_SNAPSHOT,
                "id": uuid4(),
            },
            target_events=["completed"],
        )
