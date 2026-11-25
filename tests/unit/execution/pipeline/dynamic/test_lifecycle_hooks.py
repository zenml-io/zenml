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
"""End-to-end tests for pipeline-level lifecycle hooks."""

from typing import List, Optional

import pytest

from zenml import pipeline, step, wait
from zenml.client import Client
from zenml.enums import (
    ExecutionStatus,
    HookType,
    RunWaitConditionResolution,
)
from zenml.models import PipelineRunUpdate
from zenml.stack import Stack

_events: List[str] = []


def record_start() -> None:
    _events.append("start")


def record_init() -> None:
    _events.append("init")


def record_end(exception: Optional[BaseException] = None) -> None:
    _events.append("end")


def record_success() -> None:
    _events.append("success")


def record_failure(exception: Optional[BaseException] = None) -> None:
    _events.append("failure")


def record_cleanup() -> None:
    _events.append("cleanup")


def record_pause() -> None:
    _events.append("pause")


def record_resume() -> None:
    _events.append("resume")


def failing_init() -> None:
    raise RuntimeError("init boom")


@step
def noop_step() -> None:
    pass


@step
def raising_step() -> None:
    raise RuntimeError("step boom")


@step(on_start=record_start, on_end=record_end)
def hooked_step() -> None:
    pass


def _run_hook_types(pipeline_run_id) -> List[HookType]:
    invocations = Client().list_hook_invocations(
        pipeline_run_id=pipeline_run_id,
        sort_by="asc:created",
        size=100,
    )
    run_types = {
        HookType.RUN_START,
        HookType.RUN_END,
        HookType.RUN_SUCCESS,
        HookType.RUN_FAILURE,
        HookType.RUN_PAUSE,
        HookType.RUN_RESUME,
    }
    return [i.hook_type for i in invocations.items if i.hook_type in run_types]


def _step_hook_types(pipeline_run_id) -> List[HookType]:
    invocations = Client().list_hook_invocations(
        pipeline_run_id=pipeline_run_id,
        sort_by="asc:created",
        size=100,
    )
    step_types = {
        HookType.STEP_START,
        HookType.STEP_END,
        HookType.STEP_SUCCESS,
        HookType.STEP_FAILURE,
    }
    return [
        i.hook_type for i in invocations.items if i.hook_type in step_types
    ]


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_start=record_start,
    on_init=record_init,
    on_end=record_end,
    on_success=record_success,
    on_failure=record_failure,
    on_cleanup=record_cleanup,
)
def dynamic_success_pipeline() -> None:
    noop_step()


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_start=record_start,
    on_init=record_init,
    on_end=record_end,
    on_success=record_success,
    on_failure=record_failure,
    on_cleanup=record_cleanup,
)
def dynamic_failure_pipeline() -> None:
    raising_step()


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_start=record_start,
    on_init=failing_init,
    on_end=record_end,
    on_success=record_success,
    on_failure=record_failure,
    on_cleanup=record_cleanup,
)
def dynamic_init_failure_pipeline() -> None:
    noop_step()


@pipeline(
    enable_cache=False,
    on_start=record_start,
    on_end=record_end,
    on_success=record_success,
    on_failure=record_failure,
)
def static_pipeline() -> None:
    noop_step()


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_start=record_start,
    on_end=record_end,
    on_success=record_success,
    on_failure=record_failure,
)
def dynamic_pipeline_with_step_hooks() -> None:
    hooked_step()


def test_dynamic_success_fires_run_hooks_in_order():
    """Tests run hook firing and order for a successful dynamic run."""
    _events.clear()
    run = dynamic_success_pipeline()
    assert run.status.is_successful

    assert _events.index("start") < _events.index("init")
    assert _events.index("end") < _events.index("success")
    assert _events[-1] == "cleanup"
    assert "failure" not in _events

    types = _run_hook_types(run.id)
    assert types.count(HookType.RUN_START) == 1
    assert types.count(HookType.RUN_END) == 1
    assert types.count(HookType.RUN_SUCCESS) == 1
    assert types.count(HookType.RUN_FAILURE) == 0
    assert types.index(HookType.RUN_END) < types.index(HookType.RUN_SUCCESS)


def test_dynamic_failure_fires_run_hooks_in_order():
    """Tests run hook firing and order for a failed dynamic run."""
    _events.clear()
    with pytest.raises(BaseException, match="step boom"):
        dynamic_failure_pipeline()
    run = (
        Client()
        .list_pipeline_runs(
            pipeline="dynamic_failure_pipeline",
            sort_by="desc:created",
            size=1,
        )
        .items[0]
    )
    assert run.status.is_failed

    assert _events.index("start") < _events.index("init")
    assert _events.index("end") < _events.index("failure")
    assert _events[-1] == "cleanup"
    assert "success" not in _events

    types = _run_hook_types(run.id)
    assert types.count(HookType.RUN_START) == 1
    assert types.count(HookType.RUN_END) == 1
    assert types.count(HookType.RUN_FAILURE) == 1
    assert types.count(HookType.RUN_SUCCESS) == 0
    assert types.index(HookType.RUN_END) < types.index(HookType.RUN_FAILURE)


def test_dynamic_init_failure_still_records_start_end_failure():
    """Tests that an init hook failure still records start, end, failure."""
    _events.clear()
    with pytest.raises(BaseException):
        dynamic_init_failure_pipeline()
    run = (
        Client()
        .list_pipeline_runs(
            pipeline="dynamic_init_failure_pipeline",
            sort_by="desc:created",
            size=1,
        )
        .items[0]
    )
    assert run.status.is_failed

    types = _run_hook_types(run.id)
    assert types.count(HookType.RUN_START) == 1
    assert types.count(HookType.RUN_END) == 1
    assert types.count(HookType.RUN_FAILURE) == 1


def test_static_pipeline_fires_no_run_hooks():
    """Tests that a static pipeline produces no run-level hook rows."""
    _events.clear()
    run = static_pipeline()
    assert run.status.is_successful
    assert _run_hook_types(run.id) == []


def test_dynamic_pipeline_hooks_do_not_propagate_to_steps():
    """Tests that dynamic pipeline-level hooks fire at run scope only."""
    _events.clear()
    run = dynamic_success_pipeline()
    assert run.status.is_successful
    assert _step_hook_types(run.id) == []


def test_dynamic_step_keeps_its_own_hooks():
    """Tests that a dynamic step still fires its own configured hooks."""
    _events.clear()
    run = dynamic_pipeline_with_step_hooks()
    assert run.status.is_successful
    step_types = _step_hook_types(run.id)
    assert HookType.STEP_START in step_types
    assert HookType.STEP_END in step_types


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_start=record_start,
    on_end=record_end,
    on_success=record_success,
    on_failure=record_failure,
    on_pause=record_pause,
    on_resume=record_resume,
)
def pausing_pipeline() -> None:
    wait(timeout=2, poll_interval=1)
    noop_step()


def test_pause_and_resume_fire_hooks():
    """Tests hook firing when a run pauses and is resumed."""
    _events.clear()
    run = pausing_pipeline()
    assert run is not None
    run = Client().get_pipeline_run(run.id, hydrate=True)
    assert run.status == ExecutionStatus.PAUSED

    assert _events == ["start", "pause"]
    types = _run_hook_types(run.id)
    assert types == [HookType.RUN_START, HookType.RUN_PAUSE]

    conditions = Client().list_run_wait_conditions(
        pipeline_run=run.id, status="pending"
    )
    assert conditions.total == 1
    Client().resolve_run_wait_condition(
        run_wait_condition_id=conditions.items[0].id,
        resolution=RunWaitConditionResolution.CONTINUE,
    )

    Client().zen_store.update_run(
        run_id=run.id,
        run_update=PipelineRunUpdate(status=ExecutionStatus.RESUMING),
    )
    stack = Stack.from_model(Client().active_stack_model)
    assert run.snapshot is not None
    stack.orchestrator.resume_run(snapshot=run.snapshot, run=run, stack=stack)

    run = Client().get_pipeline_run(run.id, hydrate=True)
    assert run.status.is_successful

    assert _events == ["start", "pause", "resume", "end", "success"]
    types = _run_hook_types(run.id)
    assert types == [
        HookType.RUN_START,
        HookType.RUN_PAUSE,
        HookType.RUN_RESUME,
        HookType.RUN_END,
        HookType.RUN_SUCCESS,
    ]
