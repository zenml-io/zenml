#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from typing import Optional
from uuid import uuid4

import pytest

from zenml import save_artifact
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import (
    ArtifactSaveType,
    HookType,
    StepRunInputArtifactType,
)
from zenml.models import (
    PipelineRunResponse,
    PipelineSnapshotResponse,
    StepRunResponse,
)
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators.step_launcher import StepRunner
from zenml.stack import Stack
from zenml.steps import step

HOOK_MODULE = "tests.unit.orchestrators.test_step_runner"

_flaky_calls = {"count": 0}


@step
def successful_step() -> None:
    pass


@step
def failing_step() -> None:
    raise RuntimeError()


@step
def flaky_step() -> None:
    _flaky_calls["count"] += 1
    if _flaky_calls["count"] < 3:
        raise RuntimeError()


def on_start_hook() -> None:
    pass


def on_end_hook(exception: Optional[BaseException] = None) -> None:
    pass


def on_success_hook() -> None:
    pass


def on_failure_hook(exception: Optional[BaseException] = None) -> None:
    pass


def _step_with_hooks(source: str) -> Step:
    """Builds a step whose config sets all four step lifecycle hooks."""
    return Step.model_validate(
        {
            "spec": {"source": source, "upstream_steps": []},
            "config": {
                "name": "step_name",
                "start_hook_source": f"{HOOK_MODULE}.on_start_hook",
                "end_hook_source": f"{HOOK_MODULE}.on_end_hook",
                "success_hook_source": f"{HOOK_MODULE}.on_success_hook",
                "failure_hook_source": f"{HOOK_MODULE}.on_failure_hook",
            },
        }
    )


def _hook_step_run_info(
    step: Step,
    snapshot: PipelineSnapshotResponse,
    step_run: StepRunResponse,
) -> StepRunInfo:
    """Builds step run info for a hook-configured step."""
    return StepRunInfo(
        step_run_id=uuid4(),
        run_id=uuid4(),
        run_name="run_name",
        pipeline_step_name="step_name",
        config=step.config,
        spec=step.spec,
        pipeline=PipelineConfiguration(name="pipeline_name"),
        snapshot=snapshot,
        force_write_logs=lambda: None,
        step_run=step_run,
    )


def _patch_step_runner_io(mocker):
    """Patches step runner IO and captures fired hooks.

    Returns:
        A list of (hook_type, optional_args) tuples for each fired hook.
    """
    fired = []
    mocker.patch(
        "zenml.orchestrators.step_runner.run_lifecycle_hook",
        side_effect=lambda source, hook_type, optional_args=None: fired.append(
            (hook_type, optional_args or ())
        ),
    )
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
    return fired


def test_running_a_successful_step(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """Tests that running a successful step runs the step entrypoint
    and correctly prepares/cleans up."""
    mock_prepare_step_run = mocker.patch.object(Stack, "prepare_step_run")
    mock_cleanup_step_run = mocker.patch.object(Stack, "cleanup_step_run")
    mocker.patch(
        "zenml.artifacts.utils.save_artifact",
        return_value=uuid4(),
    )
    mock_publish_successful_step_run = mocker.patch(
        "zenml.orchestrators.step_runner.publish_successful_step_run"
    )
    mocker.patch(
        "zenml.orchestrators.step_runner.setup_logging_context",
        return_value=mocker.MagicMock(
            __enter__=lambda s: None, __exit__=lambda s, *a: None
        ),
    )

    step = Step.model_validate(
        {
            "spec": {
                "source": "tests.unit.orchestrators.test_step_runner.successful_step",
                "upstream_steps": [],
            },
            "config": {
                "name": "step_name",
            },
        }
    )
    pipeline_config = PipelineConfiguration(name="pipeline_name")
    step_run_info = StepRunInfo(
        step_run_id=uuid4(),
        run_id=uuid4(),
        run_name="run_name",
        pipeline_step_name="step_name",
        config=step.config,
        spec=step.spec,
        pipeline=pipeline_config,
        snapshot=sample_snapshot_response_model,
        force_write_logs=lambda: None,
        step_run=sample_step_run,
    )

    runner = StepRunner(step=step, stack=local_stack)
    runner.run(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        step_run_info=step_run_info,
        input_artifacts={},
        output_artifact_uris={},
    )
    mock_prepare_step_run.assert_called_with(info=step_run_info)
    mock_cleanup_step_run.assert_called_with(
        info=step_run_info, step_failed=False
    )
    mock_publish_successful_step_run.assert_called_once()


def test_running_a_failing_step(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """Tests that running a failing step runs the step entrypoint
    and correctly prepares/cleans up."""

    mock_prepare_step_run = mocker.patch.object(Stack, "prepare_step_run")
    mock_cleanup_step_run = mocker.patch.object(Stack, "cleanup_step_run")
    mocker.patch(
        "zenml.artifacts.utils.save_artifact",
        return_value=uuid4(),
    )
    mock_publish_successful_step_run = mocker.patch(
        "zenml.orchestrators.step_runner.publish_successful_step_run"
    )
    mock_publish_failed_step_run = mocker.patch(
        "zenml.orchestrators.step_runner.publish_failed_step_run"
    )
    mocker.patch(
        "zenml.orchestrators.step_runner.setup_logging_context",
        return_value=mocker.MagicMock(
            __enter__=lambda s: None, __exit__=lambda s, *a: None
        ),
    )

    step = Step.model_validate(
        {
            "spec": {
                "source": "tests.unit.orchestrators.test_step_runner.failing_step",
                "upstream_steps": [],
            },
            "config": {
                "name": "step_name",
            },
        }
    )
    pipeline_config = PipelineConfiguration(name="pipeline_name")
    step_run_info = StepRunInfo(
        step_run_id=uuid4(),
        run_id=uuid4(),
        run_name="run_name",
        pipeline_step_name="step_name",
        config=step.config,
        spec=step.spec,
        pipeline=pipeline_config,
        snapshot=sample_snapshot_response_model,
        force_write_logs=lambda: None,
        step_run=sample_step_run,
    )

    runner = StepRunner(step=step, stack=local_stack)
    with pytest.raises(RuntimeError):
        runner.run(
            pipeline_run=sample_pipeline_run,
            step_run=sample_step_run,
            step_run_info=step_run_info,
            input_artifacts={},
            output_artifact_uris={},
        )

    mock_prepare_step_run.assert_called_with(info=step_run_info)
    mock_cleanup_step_run.assert_called_with(
        info=step_run_info, step_failed=True
    )
    mock_publish_failed_step_run.assert_called_with(
        step_run_id=step_run_info.step_run_id
    )
    mock_publish_successful_step_run.assert_not_called()


def test_loading_unmaterialized_input_artifact(local_stack, clean_client):
    """Tests that having an input of type `UnmaterializedArtifact` does not
    materialize the artifact but instead returns the response model."""

    artifact_response = save_artifact(
        42, "main_answer", save_type=ArtifactSaveType.STEP_OUTPUT
    ).get_hydrated_version()

    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
            },
            "config": {
                "name": "step_name",
            },
        }
    )
    runner = StepRunner(step=step, stack=local_stack)
    artifact = runner._load_input_artifact(
        artifact=artifact_response, data_type=UnmaterializedArtifact
    )
    assert artifact.model_dump() == artifact_response.model_dump()


def test_loading_input_artifact_without_specified_data_type(
    local_stack, clean_client
):
    """Tests that loading an artifact without a specified data type falls
    back to the data type of the artifact response."""

    artifact_response = save_artifact(
        42, "main_answer", save_type=ArtifactSaveType.STEP_OUTPUT
    )
    step_run_input_response = StepRunInputResponse(
        **artifact_response.get_hydrated_version().model_dump(),
        input_type=StepRunInputArtifactType.STEP_OUTPUT,
    )

    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
            },
            "config": {
                "name": "step_name",
            },
        }
    )
    runner = StepRunner(step=step, stack=local_stack)
    data = runner._load_input_artifact(
        artifact=step_run_input_response, data_type=None
    )
    assert isinstance(data, int)
    assert data == 42


def test_step_hooks_fire_on_successful_attempt(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """Tests that a successful attempt fires start, end, and success hooks."""
    fired = _patch_step_runner_io(mocker)
    step = _step_with_hooks(f"{HOOK_MODULE}.successful_step")
    step_run_info = _hook_step_run_info(
        step, sample_snapshot_response_model, sample_step_run
    )

    runner = StepRunner(step=step, stack=local_stack)
    runner.run(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        step_run_info=step_run_info,
        input_artifacts={},
        output_artifact_uris={},
    )

    types = [hook_type for hook_type, _ in fired]
    end_calls = [
        args for hook_type, args in fired if hook_type == HookType.STEP_END
    ]
    assert types.count(HookType.STEP_START) == 1
    assert len(end_calls) == 1
    assert end_calls[0] == (None,)
    assert types.count(HookType.STEP_SUCCESS) == 1
    assert types.count(HookType.STEP_FAILURE) == 0


def test_step_hooks_fire_one_pair_per_attempt(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """Tests that two retriable failures then a success fire one pair each."""
    _flaky_calls["count"] = 0
    fired = _patch_step_runner_io(mocker)
    mock_failed = mocker.patch(
        "zenml.orchestrators.step_runner.publish_failed_step_run"
    )
    mock_failed.return_value.is_retriable = True

    step = _step_with_hooks(f"{HOOK_MODULE}.flaky_step")
    step_run_info = _hook_step_run_info(
        step, sample_snapshot_response_model, sample_step_run
    )
    runner = StepRunner(step=step, stack=local_stack)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            runner.run(
                pipeline_run=sample_pipeline_run,
                step_run=sample_step_run,
                step_run_info=step_run_info,
                input_artifacts={},
                output_artifact_uris={},
            )
    runner.run(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        step_run_info=step_run_info,
        input_artifacts={},
        output_artifact_uris={},
    )

    types = [hook_type for hook_type, _ in fired]
    end_exceptions = [
        args[0] for hook_type, args in fired if hook_type == HookType.STEP_END
    ]
    assert types.count(HookType.STEP_START) == 3
    assert isinstance(end_exceptions[0], RuntimeError)
    assert isinstance(end_exceptions[1], RuntimeError)
    assert end_exceptions[2] is None
    assert types.count(HookType.STEP_SUCCESS) == 1
    assert types.count(HookType.STEP_FAILURE) == 0


def test_step_hooks_terminal_failure_fires_failure_hook(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    """Tests that a retriable then terminal failure fires one failure hook."""
    fired = _patch_step_runner_io(mocker)
    mock_failed = mocker.patch(
        "zenml.orchestrators.step_runner.publish_failed_step_run"
    )
    mock_failed.side_effect = [
        mocker.Mock(is_retriable=True),
        mocker.Mock(is_retriable=False),
    ]

    step = _step_with_hooks(f"{HOOK_MODULE}.failing_step")
    step_run_info = _hook_step_run_info(
        step, sample_snapshot_response_model, sample_step_run
    )
    runner = StepRunner(step=step, stack=local_stack)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            runner.run(
                pipeline_run=sample_pipeline_run,
                step_run=sample_step_run,
                step_run_info=step_run_info,
                input_artifacts={},
                output_artifact_uris={},
            )

    types = [hook_type for hook_type, _ in fired]
    end_calls = [
        args for hook_type, args in fired if hook_type == HookType.STEP_END
    ]
    failure_calls = [
        args for hook_type, args in fired if hook_type == HookType.STEP_FAILURE
    ]
    assert types.count(HookType.STEP_START) == 2
    assert len(end_calls) == 2
    assert isinstance(end_calls[0][0], RuntimeError)
    assert isinstance(end_calls[1][0], RuntimeError)
    assert len(failure_calls) == 1
    assert isinstance(failure_calls[0][0], RuntimeError)
    assert types.count(HookType.STEP_SUCCESS) == 0
