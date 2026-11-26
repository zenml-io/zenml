#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests that the store sends the run-ended analytics event once per run end."""

from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest
from sqlmodel import Session

from zenml import pipeline, step
from zenml.analytics.enums import AnalyticsEvent
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunUpdate, StepRunUpdate
from zenml.utils.time_utils import utc_now
from zenml.zen_stores import sql_zen_store
from zenml.zen_stores.schemas import PipelineRunSchema


@step
def noop_step() -> None:
    """Step that does nothing."""


@pipeline(enable_cache=False)
def single_step_pipeline() -> None:
    """Pipeline with a single step."""
    noop_step()


@step
def producer_step() -> int:
    """Step that produces a value.

    Returns:
        The value.
    """
    return 1


@step
def consumer_step(value: int) -> None:
    """Step that consumes a value.

    Args:
        value: The value.
    """


@pipeline
def two_step_pipeline() -> None:
    """Pipeline with two dependent steps."""
    consumer_step(producer_step())


def _record_run_ended_events(
    monkeypatch: pytest.MonkeyPatch,
) -> List[Dict[str, Any]]:
    """Record the run-ended events the store sends from now on.

    Args:
        monkeypatch: The pytest monkeypatch fixture.

    Returns:
        The list that the metadata of each sent event is appended to.
    """
    events: List[Dict[str, Any]] = []

    class _RecordingTrackHandler:
        def __init__(
            self,
            event: AnalyticsEvent,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> None:
            self.event = event
            self.metadata: Dict[str, Any] = metadata or {}

        def __enter__(self) -> "_RecordingTrackHandler":
            return self

        def __exit__(self, *_: Any) -> None:
            if self.event == AnalyticsEvent.RUN_PIPELINE_ENDED:
                events.append(self.metadata)

    monkeypatch.setattr(sql_zen_store, "track_handler", _RecordingTrackHandler)
    return events


def _reset_run(
    client: Client,
    run_id: UUID,
    status: ExecutionStatus = ExecutionStatus.RUNNING,
) -> None:
    """Put a finished run back into progress.

    Args:
        client: The client whose store holds the run.
        run_id: The ID of the run.
        status: The status the run has while in progress.
    """
    with Session(client.zen_store.engine) as session:
        run_schema = session.get(PipelineRunSchema, run_id)
        run_schema.status = status.value
        run_schema.in_progress = True
        run_schema.end_time = None
        session.add(run_schema)
        session.commit()


def test_run_ended_is_sent_only_when_the_run_ends(
    clean_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Updates of an already finished run don't send the event again."""
    run = single_step_pipeline()
    _reset_run(clean_client, run.id)
    events = _record_run_ended_events(monkeypatch)
    store = clean_client.zen_store

    store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )

    assert len(events) == 1
    assert events[0]["pipeline_run_id"] == run.id
    assert events[0]["status"] == ExecutionStatus.COMPLETED
    assert events[0]["end_time"] is not None

    # The orchestrator publishing its final status again and a late step
    # update both recompute the status of the finished run.
    store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )
    step_run = clean_client.get_pipeline_run(run.id).steps["noop_step"]
    store.update_run_step(
        step_run_id=step_run.id,
        step_run_update=StepRunUpdate(end_time=utc_now()),
    )

    assert len(events) == 1


def test_run_ended_is_sent_once_when_the_run_fails(
    clean_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Publishing the failed status again doesn't send the event again."""
    run = single_step_pipeline()
    _reset_run(clean_client, run.id)
    events = _record_run_ended_events(monkeypatch)
    store = clean_client.zen_store

    store.update_run(run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED))
    store.update_run(run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED))

    assert len(events) == 1
    assert events[0]["status"] == ExecutionStatus.FAILED


def test_run_ended_is_sent_when_a_failed_run_stops_being_in_progress(
    clean_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run that failed while other steps still ran ends once they stop."""
    run = single_step_pipeline()
    _reset_run(clean_client, run.id, status=ExecutionStatus.FAILED)
    events = _record_run_ended_events(monkeypatch)
    store = clean_client.zen_store

    store.update_run(run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED))
    store.update_run(run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED))

    assert len(events) == 1
    assert events[0]["status"] == ExecutionStatus.FAILED
    assert events[0]["end_time"] is not None


@pytest.mark.parametrize(
    "step_status", [ExecutionStatus.CACHED, ExecutionStatus.SKIPPED]
)
def test_run_ended_is_sent_once_for_runs_without_executed_steps(
    clean_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    step_status: ExecutionStatus,
) -> None:
    """A run whose steps are all cached or skipped sends the event once."""
    cached = step_status == ExecutionStatus.CACHED
    run_pipeline = two_step_pipeline.with_options(enable_cache=cached)
    original_run = run_pipeline()
    events = _record_run_ended_events(monkeypatch)

    if cached:
        run = run_pipeline()
    else:
        run = run_pipeline.replay(
            pipeline_run=original_run.id, skip_successful_steps=True
        )

    run = clean_client.get_pipeline_run(run.id)
    assert len(run.steps) == 2
    assert {step.status for step in run.steps.values()} == {step_status}
    assert run.status == ExecutionStatus.COMPLETED
    assert len(events) == 1
    assert events[0]["pipeline_run_id"] == run.id
    assert events[0]["status"] == ExecutionStatus.COMPLETED

    clean_client.zen_store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )

    assert len(events) == 1
