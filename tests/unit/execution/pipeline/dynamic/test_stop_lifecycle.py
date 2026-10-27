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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Run stopping through real local dynamic execution and an isolated store."""

import threading
from typing import List

import pytest

from zenml import pipeline, step
from zenml.client import Client
from zenml.enums import ExecutionMode, ExecutionStatus, PipelineRunStopMode
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.models import PipelineRunUpdate
from zenml.stack import Stack

_finished: List[str] = []
_attempt_started = threading.Event()
_attempt_release = threading.Event()


@step
def request_graceful_stop(failed: bool) -> None:
    """Request stop from an admitted step and finish its current attempt."""
    context = DynamicPipelineRunContext.get()
    assert context is not None
    store = Client().zen_store
    if failed:
        store.update_run(
            context.run.id,
            PipelineRunUpdate(status=ExecutionStatus.FAILED),
        )
    store.update_run(
        context.run.id,
        PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL),
    )
    _finished.append("admitted")


@step
def forbidden_new_step() -> None:
    """Record work that must never be admitted after cancellation."""
    _finished.append("forbidden")


@pipeline(dynamic=True, enable_cache=False)
def stopped_pipeline(failed: bool) -> None:
    """Stop between two synchronous invocations."""
    request_graceful_stop(failed)
    forbidden_new_step()


@pytest.mark.parametrize("execution_mode", list(ExecutionMode))
@pytest.mark.parametrize("failed", [False, True])
def test_graceful_stop_drains_attempt_and_fences_next_invocation(
    execution_mode: ExecutionMode, failed: bool
) -> None:
    """The admitted attempt completes and an existing run failure survives."""
    _finished.clear()
    run = stopped_pipeline.with_options(execution_mode=execution_mode)(failed)
    run = Client().get_pipeline_run(run.id)

    assert _finished == ["admitted"]
    assert run.status == (
        ExecutionStatus.FAILED if failed else ExecutionStatus.STOPPED
    )
    assert run.stop_mode == PipelineRunStopMode.GRACEFUL
    assert not run.in_progress
    assert (
        run.steps["request_graceful_stop"].status == ExecutionStatus.COMPLETED
    )
    assert "forbidden_new_step" not in run.steps


@step
def request_root_stop() -> None:
    """Stop remaining root execution after its outcome has already failed."""
    context = DynamicPipelineRunContext.get()
    assert context is not None
    root_id = context.run.root_run_id or context.run.id
    Client().zen_store.update_run(
        root_id,
        PipelineRunUpdate(status=ExecutionStatus.FAILED),
    )
    Client().zen_store.update_run(
        root_id,
        PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL),
    )
    _finished.append("root-stop")


@pipeline(dynamic=True, enable_cache=False)
def stopped_child() -> None:
    """Keep a completed attempt reusable while stopping subsequent work."""
    request_root_stop()
    forbidden_new_step()


@pipeline(dynamic=True, enable_cache=False)
def stopped_parent() -> None:
    """Run the child in the shared controller."""
    stopped_child()


def test_resume_reuses_stopped_child_after_clearing_inherited_intent() -> None:
    """A safe root resume reopens the stopped child's admission as well."""
    _finished.clear()
    run = stopped_parent()
    run = Client().get_pipeline_run(run.id)
    assert run.status == ExecutionStatus.FAILED
    assert _finished == ["root-stop"]
    children = Client().list_pipeline_runs(parent_run_id=run.id)
    assert children.total == 1
    child_id = children.items[0].id
    assert children.items[0].stop_mode == PipelineRunStopMode.GRACEFUL
    assert not children.items[0].in_progress

    Client().zen_store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.RESUMING)
    )
    stack = Stack.from_model(Client().active_stack_model)
    assert run.snapshot is not None
    stack.orchestrator.resume_run(snapshot=run.snapshot, run=run, stack=stack)

    run = Client().get_pipeline_run(run.id)
    child = Client().get_pipeline_run(child_id)
    assert run.status == ExecutionStatus.COMPLETED
    assert child.status == ExecutionStatus.COMPLETED
    assert child.stop_mode is None
    assert _finished == ["root-stop", "forbidden"]


@step
def draining_attempt() -> None:
    """Keep an admitted attempt active across the graceful stop request."""
    _attempt_started.set()
    assert _attempt_release.wait(timeout=5)
    _finished.append("drained")


@pipeline(dynamic=True, enable_cache=False)
def concurrently_stopped_pipeline() -> None:
    """Stop queued work while an already-admitted attempt is blocked."""
    future = draining_attempt.submit()
    try:
        assert _attempt_started.wait(timeout=5)
        forbidden_new_step.submit()
        context = DynamicPipelineRunContext.get()
        assert context is not None
        Client().zen_store.update_run(
            context.run.id,
            PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL),
        )
        context.runner.request_stop(PipelineRunStopMode.GRACEFUL)
    finally:
        _attempt_release.set()
    future.wait()


def test_graceful_stop_drains_running_future_and_cancels_queued_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelling pending executor work does not cancel an admitted attempt."""
    _finished.clear()
    _attempt_started.clear()
    _attempt_release.clear()
    monkeypatch.setenv("ZENML_DYNAMIC_PIPELINE_WORKER_COUNT", "1")
    run = concurrently_stopped_pipeline()
    run = Client().get_pipeline_run(run.id)

    assert _finished == ["drained"]
    assert run.status == ExecutionStatus.STOPPED
    assert not run.in_progress
    assert run.steps["draining_attempt"].status == ExecutionStatus.COMPLETED
    assert "forbidden_new_step" not in run.steps
