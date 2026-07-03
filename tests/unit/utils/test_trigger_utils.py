from uuid import uuid4

import pytest
from mock import Mock, patch
from pydantic import ValidationError

from zenml.enums import (
    PipelineEvent,
    PipelineRunEvent,
    PipelineSnapshotEvent,
    SourceType,
    TriggerRunConcurrency,
)
from zenml.utils import trigger_utils


def test_list_supported_events():
    run_events = trigger_utils.list_supported_events(
        source_type=SourceType.PIPELINE_RUN
    )

    assert len(run_events) > 1
    assert "completed" in run_events

    pipeline_events = trigger_utils.list_supported_events(
        source_type=SourceType.PIPELINE
    )

    assert len(pipeline_events) > 1
    assert "run_completed" in pipeline_events

    snapshot_events = trigger_utils.list_supported_events(
        source_type=SourceType.PIPELINE_SNAPSHOT
    )

    assert len(snapshot_events) > 1
    assert "run_completed" in snapshot_events

    with pytest.raises(ValidationError):
        trigger_utils.list_supported_events(source_type="snapshot")


def test_create_platform_event_trigger_happy_path():
    source_pipeline_id = uuid4()
    expected_response = Mock()

    mock_client = Mock()
    mock_client.create_platform_event_trigger.return_value = expected_response

    with patch.object(trigger_utils, "Client", return_value=mock_client):
        result = trigger_utils.create_platform_event_trigger(
            name="my-trigger",
            source_pipeline_id=source_pipeline_id,
            target_events=[PipelineEvent.RUN_COMPLETED],
            active=False,
            concurrency=TriggerRunConcurrency.SUBMIT,
        )

    assert result is expected_response
    mock_client.create_platform_event_trigger.assert_called_once_with(
        name="my-trigger",
        source_type=SourceType.PIPELINE,
        source_id=source_pipeline_id,
        target_events=[str(PipelineEvent.RUN_COMPLETED.value)],
        active=False,
        concurrency=TriggerRunConcurrency.SUBMIT,
    )


def test_create_platform_event_trigger_with_snapshot_source():
    source_pipeline_snapshot_id = uuid4()
    expected_response = Mock()

    mock_client = Mock()
    mock_client.create_platform_event_trigger.return_value = expected_response

    with patch.object(trigger_utils, "Client", return_value=mock_client):
        result = trigger_utils.create_platform_event_trigger(
            name="my-snapshot-trigger",
            source_pipeline_snapshot_id=source_pipeline_snapshot_id,
            target_events=[PipelineSnapshotEvent.RUN_COMPLETED],
            active=False,
            concurrency=TriggerRunConcurrency.SUBMIT,
        )

    assert result is expected_response
    mock_client.create_platform_event_trigger.assert_called_once_with(
        name="my-snapshot-trigger",
        source_type=SourceType.PIPELINE_SNAPSHOT,
        source_id=source_pipeline_snapshot_id,
        target_events=[str(PipelineSnapshotEvent.RUN_COMPLETED.value)],
        active=False,
        concurrency=TriggerRunConcurrency.SUBMIT,
    )


@pytest.mark.parametrize(
    "kwargs, expected_message",
    [
        (
            {
                "source_pipeline_id": uuid4(),
                "source_pipeline_run_id": uuid4(),
                "source_pipeline_snapshot_id": uuid4(),
            },
            "You can not provide more than 1 source option",
        ),
        (
            {},
            "You must specify at least one source option",
        ),
    ],
)
def test_create_platform_event_trigger_validations(kwargs, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        trigger_utils.create_platform_event_trigger(
            name="my-trigger",
            target_events=[PipelineEvent.RUN_COMPLETED],
            **kwargs,
        )


def test_update_platform_event_trigger_happy_path():
    trigger_id = uuid4()
    expected_response = Mock()

    mock_client = Mock()
    mock_client.update_platform_event_trigger.return_value = expected_response

    with patch.object(trigger_utils, "Client", return_value=mock_client):
        result = trigger_utils.update_platform_event_trigger(
            trigger_name_id_or_prefix=trigger_id,
            name="updated-trigger",
            target_events=[PipelineRunEvent.COMPLETED],
            active=True,
            concurrency=TriggerRunConcurrency.SKIP,
        )

    assert result is expected_response
    mock_client.update_platform_event_trigger.assert_called_once_with(
        trigger_name_id_or_prefix=trigger_id,
        name="updated-trigger",
        active=True,
        source_id=None,
        source_type=None,
        target_events=[str(PipelineRunEvent.COMPLETED.value)],
        concurrency=TriggerRunConcurrency.SKIP,
    )


def test_update_platform_event_trigger_allows_single_source_pipeline_id():
    """Covers the current validation bug: a single source should be allowed."""
    trigger_id = uuid4()
    source_pipeline_id = uuid4()
    expected_response = Mock()

    mock_client = Mock()
    mock_client.update_platform_event_trigger.return_value = expected_response

    with patch.object(trigger_utils, "Client", return_value=mock_client):
        result = trigger_utils.update_platform_event_trigger(
            trigger_name_id_or_prefix=trigger_id,
            source_pipeline_id=source_pipeline_id,
            target_events=[PipelineEvent.RUN_COMPLETED],
        )

    assert result is expected_response
    mock_client.update_platform_event_trigger.assert_called_once_with(
        trigger_name_id_or_prefix=trigger_id,
        name=None,
        active=None,
        source_id=source_pipeline_id,
        source_type=SourceType.PIPELINE,
        target_events=[str(PipelineEvent.RUN_COMPLETED.value)],
        concurrency=None,
    )


def test_update_platform_event_trigger_allows_single_source_snapshot_id():
    trigger_id = uuid4()
    source_pipeline_snapshot_id = uuid4()
    expected_response = Mock()

    mock_client = Mock()
    mock_client.update_platform_event_trigger.return_value = expected_response

    with patch.object(trigger_utils, "Client", return_value=mock_client):
        result = trigger_utils.update_platform_event_trigger(
            trigger_name_id_or_prefix=trigger_id,
            source_pipeline_snapshot_id=source_pipeline_snapshot_id,
            target_events=[PipelineSnapshotEvent.RUN_COMPLETED],
        )

    assert result is expected_response
    mock_client.update_platform_event_trigger.assert_called_once_with(
        trigger_name_id_or_prefix=trigger_id,
        name=None,
        active=None,
        source_id=source_pipeline_snapshot_id,
        source_type=SourceType.PIPELINE_SNAPSHOT,
        target_events=[str(PipelineSnapshotEvent.RUN_COMPLETED.value)],
        concurrency=None,
    )
