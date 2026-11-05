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
"""Regression tests for https://github.com/zenml-io/zenml/issues/4846.

When a pipeline is served by a deployer and the active stack uses an
orchestrator with ``run_init_cleanup_at_step_level=True`` (e.g. the
Kubernetes orchestrator), the step runner used to re-run the init and
cleanup hooks for every invocation. The cleanup hook tears down the
process-wide ``RunContext`` singleton that the deployment service
initialized once at startup, so concurrent invocations race: one request's
cleanup destroys the run context while another request is mid-step.
"""

import threading
from typing import List
from unittest.mock import PropertyMock
from uuid import uuid4

import pytest

from zenml import get_step_context, step
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.deployers.server import runtime
from zenml.models import (
    PipelineRunResponse,
    PipelineSnapshotResponse,
    StepRunResponse,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.orchestrators.step_launcher import StepRunner
from zenml.stack import Stack
from zenml.steps.step_context import RunContext, get_or_create_run_context

_slow_step_started = threading.Event()
_other_invocation_done = threading.Event()
_state_read_errors: List[BaseException] = []


@step
def read_state_step() -> None:
    """Reads the pipeline state, like a serving step would."""
    try:
        _ = get_step_context().pipeline_state
    except BaseException as e:
        _state_read_errors.append(e)


@step
def slow_read_state_step() -> None:
    """Waits until the concurrent invocation finished, then reads state."""
    _slow_step_started.set()
    _other_invocation_done.wait(timeout=10)
    try:
        _ = get_step_context().pipeline_state
    except BaseException as e:
        _state_read_errors.append(e)


class StepLevelHooksOrchestrator(LocalOrchestrator):
    """Stand-in for orchestrators with isolated step environments.

    Like e.g. the Kubernetes orchestrator, the init/cleanup hooks run at
    step level and use the base hook implementations.
    """

    @property
    def run_init_cleanup_at_step_level(self) -> bool:
        """Whether the orchestrator runs the init/cleanup hooks at step level.

        Returns:
            Always True, to mimic remote orchestrators.
        """
        return True

    run_init_hook = BaseOrchestrator.run_init_hook
    run_cleanup_hook = BaseOrchestrator.run_cleanup_hook


@pytest.fixture(autouse=True)
def clean_run_context_and_sync_state():
    """Provides a clean run context and synchronization state per test."""
    RunContext._clear()
    _slow_step_started.clear()
    _other_invocation_done.clear()
    _state_read_errors.clear()
    yield
    _other_invocation_done.set()
    RunContext._clear()


def _build_step(source: str) -> Step:
    return Step.model_validate(
        {
            "spec": {"source": source, "upstream_steps": []},
            "config": {"name": "step_name"},
        }
    )


def _build_step_run_info(
    step_: Step,
    snapshot: PipelineSnapshotResponse,
    step_run: StepRunResponse,
) -> StepRunInfo:
    return StepRunInfo(
        step_run_id=uuid4(),
        run_id=uuid4(),
        run_name="run_name",
        pipeline_step_name="step_name",
        config=step_.config,
        spec=step_.spec,
        pipeline=PipelineConfiguration(name="pipeline_name"),
        snapshot=snapshot,
        force_write_logs=lambda: None,
        step_run=step_run,
    )


def _patch_environment(mocker, local_stack, snapshot):
    """Prepares the deployment serving environment.

    Patches IO like the other step runner tests, makes the stack's
    orchestrator component a step-level-hooks orchestrator, and attaches
    the snapshot to the pipeline run.
    """
    mocker.patch.object(Stack, "prepare_step_run")
    mocker.patch.object(Stack, "cleanup_step_run")
    mocker.patch("zenml.artifacts.utils.save_artifact", return_value=uuid4())
    mocker.patch("zenml.orchestrators.step_runner.publish_successful_step_run")
    mocker.patch(
        "zenml.orchestrators.step_runner.setup_logging_context",
        return_value=mocker.MagicMock(
            __enter__=lambda s: None, __exit__=lambda s, *a: None
        ),
    )
    orchestrator = StepLevelHooksOrchestrator(
        name="step-level-hooks",
        id=uuid4(),
        config=local_stack.orchestrator.config,
        flavor="local",
        type=local_stack.orchestrator.type,
        user=uuid4(),
        created=local_stack.orchestrator.created,
        updated=local_stack.orchestrator.updated,
    )
    mocker.patch.object(
        Stack,
        "orchestrator",
        new_callable=PropertyMock,
        return_value=orchestrator,
    )
    mocker.patch.object(
        PipelineRunResponse,
        "snapshot",
        new_callable=PropertyMock,
        return_value=snapshot,
    )


def _invoke(
    step_source: str,
    local_stack,
    pipeline_run,
    step_run,
    snapshot,
) -> None:
    """Simulates one deployment invocation.

    The deployment service starts the request-scoped runtime context,
    then runs the step in-process.
    """
    runtime.start(
        request_id=str(uuid4()),
        snapshot=snapshot,
        parameters={},
    )
    try:
        step_ = _build_step(step_source)
        runner = StepRunner(step=step_, stack=local_stack)
        runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            step_run_info=_build_step_run_info(step_, snapshot, step_run),
            input_artifacts={},
            output_artifact_uris={},
        )
    finally:
        runtime.stop()


def test_deployment_invocation_does_not_tear_down_run_context(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """A single invocation must leave the boot-time run context intact."""
    _patch_environment(mocker, local_stack, sample_snapshot_response_model)

    # The deployment service runs the init hook once at startup.
    BaseOrchestrator.run_init_hook(sample_snapshot_response_model)
    assert get_or_create_run_context().initialized

    _invoke(
        f"{__name__}.read_state_step",
        local_stack,
        sample_pipeline_run,
        sample_step_run,
        sample_snapshot_response_model,
    )

    assert not _state_read_errors
    # The boot-time run context must survive the invocation: it is owned
    # by the deployment service, not by individual requests.
    assert get_or_create_run_context().initialized


def test_concurrent_deployment_invocations_do_not_race_on_run_context(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """Two overlapping invocations must both read the pipeline state.

    Before the fix, the fast invocation's step-level cleanup hook cleared
    the process-wide run context while the slow invocation was mid-step,
    making its ``pipeline_state`` access raise ``RuntimeError: Run context
    not initialized``.
    """
    _patch_environment(mocker, local_stack, sample_snapshot_response_model)

    def _run(step_source: str) -> None:
        _invoke(
            step_source,
            local_stack,
            sample_pipeline_run,
            sample_step_run,
            sample_snapshot_response_model,
        )

    BaseOrchestrator.run_init_hook(sample_snapshot_response_model)

    slow = threading.Thread(
        target=_run, args=(f"{__name__}.slow_read_state_step",)
    )
    fast = threading.Thread(target=_run, args=(f"{__name__}.read_state_step",))
    slow.start()
    # Only fire the fast invocation once the slow step is mid-execution,
    # so its state read is guaranteed to overlap with the fast
    # invocation's completion.
    assert _slow_step_started.wait(timeout=10)
    fast.start()
    fast.join(timeout=10)
    # The fast invocation has fully finished, including any step-level
    # cleanup hooks it may run; only now the slow step reads the state.
    _other_invocation_done.set()
    slow.join(timeout=10)

    assert not _state_read_errors, (
        f"Concurrent invocations failed with: {_state_read_errors}"
    )
