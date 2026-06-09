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

from unittest.mock import PropertyMock
from uuid import uuid4

import pytest

from zenml import save_artifact
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import ArtifactSaveType, StepRunInputArtifactType
from zenml.execution.step.utils import launch_step
from zenml.models import (
    PipelineRunResponse,
    PipelineSnapshotResponse,
    StepRunResponse,
)
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators.step_launcher import StepLauncher, StepRunner
from zenml.stack import Stack
from zenml.steps import step
from zenml.steps.step_context import get_or_create_run_context


@step
def successful_step() -> None:
    pass


@step
def failing_step() -> None:
    raise RuntimeError()


def _pipeline_run_with_snapshot(
    pipeline_run: PipelineRunResponse,
    snapshot: PipelineSnapshotResponse,
) -> PipelineRunResponse:
    return pipeline_run.model_copy(
        update={
            "resources": pipeline_run.resources.model_copy(
                update={"snapshot": snapshot}
            )
        }
    )


def _snapshot_with_stack(
    snapshot: PipelineSnapshotResponse, stack: Stack
) -> PipelineSnapshotResponse:
    return snapshot.model_copy(
        update={
            "resources": snapshot.resources.model_copy(update={"stack": stack})
        }
    )


def _successful_step_run_info(
    step: Step,
    step_run: StepRunResponse,
    snapshot: PipelineSnapshotResponse,
) -> StepRunInfo:
    pipeline_config = PipelineConfiguration(name="pipeline_name")
    return StepRunInfo(
        step_run_id=uuid4(),
        run_id=uuid4(),
        run_name="run_name",
        pipeline_step_name="step_name",
        config=step.config,
        spec=step.spec,
        pipeline=pipeline_config,
        snapshot=snapshot,
        force_write_logs=lambda: None,
        step_run=step_run,
    )


def _step_config(source: str) -> Step:
    return Step.model_validate(
        {
            "spec": {
                "source": source,
                "upstream_steps": [],
            },
            "config": {
                "name": "step_name",
            },
        }
    )


def _successful_step_config() -> Step:
    return _step_config(
        "tests.unit.orchestrators.test_step_runner.successful_step"
    )


def _failing_step_config() -> Step:
    return _step_config(
        "tests.unit.orchestrators.test_step_runner.failing_step"
    )


def _mock_successful_step_runner_dependencies(mocker):
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
    return (
        mock_prepare_step_run,
        mock_cleanup_step_run,
        mock_publish_successful_step_run,
    )


def _mock_stack_lifecycle_hooks(
    mocker,
    stack,
    init_return=True,
    init_side_effect=None,
):
    orchestrator_class = stack.orchestrator.__class__
    mocker.patch.object(
        orchestrator_class,
        "run_init_cleanup_at_step_level",
        new_callable=PropertyMock,
        return_value=True,
    )
    mock_run_init_hook = mocker.patch.object(
        orchestrator_class, "run_init_hook", return_value=init_return
    )
    if init_side_effect:
        mock_run_init_hook.side_effect = init_side_effect
    mock_run_cleanup_hook = mocker.patch.object(
        orchestrator_class, "run_cleanup_hook"
    )
    return mock_run_init_hook, mock_run_cleanup_hook


def _run_successful_step(
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
) -> StepRunInfo:
    step = _successful_step_config()
    step_run_info = _successful_step_run_info(
        step=step,
        step_run=sample_step_run,
        snapshot=sample_snapshot_response_model,
    )
    pipeline_run = _pipeline_run_with_snapshot(
        sample_pipeline_run, sample_snapshot_response_model
    )
    runner = StepRunner(step=step, stack=local_stack)
    runner.run(
        pipeline_run=pipeline_run,
        step_run=sample_step_run,
        step_run_info=step_run_info,
        input_artifacts={},
        output_artifact_uris={},
    )
    return step_run_info


def test_running_a_successful_step(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    (
        mock_prepare_step_run,
        mock_cleanup_step_run,
        mock_publish_successful_step_run,
    ) = _mock_successful_step_runner_dependencies(mocker)

    step_run_info = _run_successful_step(
        local_stack=local_stack,
        sample_pipeline_run=sample_pipeline_run,
        sample_step_run=sample_step_run,
        sample_snapshot_response_model=sample_snapshot_response_model,
    )

    mock_prepare_step_run.assert_called_with(info=step_run_info)
    mock_cleanup_step_run.assert_called_with(
        info=step_run_info, step_failed=False
    )
    mock_publish_successful_step_run.assert_called_once()


@pytest.mark.parametrize(
    "init_result, cleanup_expected",
    [
        (True, True),
        (False, False),
        (None, True),
    ],
)
def test_step_runner_cleanup_depends_on_init_result(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
    init_result,
    cleanup_expected,
):
    _mock_successful_step_runner_dependencies(mocker)
    mock_run_init_hook, mock_run_cleanup_hook = _mock_stack_lifecycle_hooks(
        mocker, local_stack, init_return=init_result
    )

    _run_successful_step(
        local_stack=local_stack,
        sample_pipeline_run=sample_pipeline_run,
        sample_step_run=sample_step_run,
        sample_snapshot_response_model=sample_snapshot_response_model,
    )

    mock_run_init_hook.assert_called_once_with(
        snapshot=sample_snapshot_response_model
    )
    if cleanup_expected:
        mock_run_cleanup_hook.assert_called_once_with(
            snapshot=sample_snapshot_response_model
        )
    else:
        mock_run_cleanup_hook.assert_not_called()


def test_step_runner_runs_cleanup_when_init_raises(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    _mock_successful_step_runner_dependencies(mocker)
    mocker.patch("zenml.orchestrators.step_runner.publish_failed_step_run")
    mock_run_init_hook, mock_run_cleanup_hook = _mock_stack_lifecycle_hooks(
        mocker,
        local_stack,
        init_side_effect=RuntimeError("init failed"),
    )

    with pytest.raises(RuntimeError, match="init failed"):
        _run_successful_step(
            local_stack=local_stack,
            sample_pipeline_run=sample_pipeline_run,
            sample_step_run=sample_step_run,
            sample_snapshot_response_model=sample_snapshot_response_model,
        )

    mock_run_init_hook.assert_called_once_with(
        snapshot=sample_snapshot_response_model
    )
    mock_run_cleanup_hook.assert_called_once_with(
        snapshot=sample_snapshot_response_model
    )


def test_step_runner_preserves_existing_run_context_when_init_returns_false(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    _mock_successful_step_runner_dependencies(mocker)
    orchestrator_class = local_stack.orchestrator.__class__
    mocker.patch.object(
        orchestrator_class,
        "run_init_cleanup_at_step_level",
        new_callable=PropertyMock,
        return_value=True,
    )
    get_or_create_run_context().initialize({"owner": "deployment-service"})

    _run_successful_step(
        local_stack=local_stack,
        sample_pipeline_run=sample_pipeline_run,
        sample_step_run=sample_step_run,
        sample_snapshot_response_model=sample_snapshot_response_model,
    )

    assert get_or_create_run_context().state == {"owner": "deployment-service"}


def test_launch_step_creates_step_launcher_without_lifecycle_argument(
    mocker,
    sample_snapshot_response_model: PipelineSnapshotResponse,
    sample_step_run: StepRunResponse,
):
    step = _successful_step_config()
    mock_launcher_class = mocker.patch(
        "zenml.execution.step.utils.StepLauncher"
    )
    mock_launcher = mock_launcher_class.return_value
    mock_launcher.launch.return_value = sample_step_run

    result = launch_step(
        snapshot=sample_snapshot_response_model,
        step=step,
        orchestrator_run_id="orchestrator-run-id",
    )

    assert result is sample_step_run
    mock_launcher_class.assert_called_once_with(
        snapshot=sample_snapshot_response_model,
        step=step,
        orchestrator_run_id="orchestrator-run-id",
        wait=True,
    )


def test_step_launcher_creates_step_runner_without_lifecycle_argument(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    step = _successful_step_config()
    snapshot = _snapshot_with_stack(
        sample_snapshot_response_model, local_stack
    )
    step_run_info = _successful_step_run_info(
        step=step,
        step_run=sample_step_run,
        snapshot=snapshot,
    )
    pipeline_run = _pipeline_run_with_snapshot(sample_pipeline_run, snapshot)
    mocker.patch.object(Stack, "from_model", return_value=local_stack)
    mock_runner_class = mocker.patch(
        "zenml.orchestrators.step_launcher.StepRunner"
    )
    mock_runner = mock_runner_class.return_value

    launcher = StepLauncher(
        snapshot=snapshot,
        step=step,
        orchestrator_run_id="orchestrator-run-id",
    )
    launcher._run_step_in_current_thread(
        pipeline_run=pipeline_run,
        step_run=sample_step_run,
        step_run_info=step_run_info,
        input_artifacts={},
        output_artifact_uris={},
    )

    mock_runner_class.assert_called_once_with(step=step, stack=local_stack)
    mock_runner.run.assert_called_once_with(
        pipeline_run=pipeline_run,
        step_run=sample_step_run,
        step_run_info=step_run_info,
        input_artifacts={},
        output_artifact_uris={},
    )


def test_running_a_failing_step(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
):
    (
        mock_prepare_step_run,
        mock_cleanup_step_run,
        mock_publish_successful_step_run,
    ) = _mock_successful_step_runner_dependencies(mocker)
    mock_publish_failed_step_run = mocker.patch(
        "zenml.orchestrators.step_runner.publish_failed_step_run"
    )

    step = _failing_step_config()
    step_run_info = _successful_step_run_info(
        step=step,
        step_run=sample_step_run,
        snapshot=sample_snapshot_response_model,
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
