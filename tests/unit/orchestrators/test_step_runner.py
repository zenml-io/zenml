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

from uuid import uuid4

import pytest

from zenml import save_artifact
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.models import PipelineRunResponse, StepRunResponse
from zenml.orchestrators.step_launcher import StepRunner
from zenml.stack import Stack
from zenml.steps import step


@step
def successful_step() -> None:
    pass


@step
def failing_step() -> None:
    raise RuntimeError()


def test_running_a_successful_step(
    mocker,
    local_stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
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

    step = Step.parse_obj(
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
        pipeline=pipeline_config,
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

    step = Step.parse_obj(
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
        pipeline=pipeline_config,
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
    mock_publish_successful_step_run.assert_not_called()


def test_loading_unmaterialized_input_artifact(local_stack, clean_client):
    """Tests that having an input of type `UnmaterializedArtifact` does not
    materialize the artifact but instead returns the response model."""
    artifact_response = save_artifact(
        42, "main_answer", manual_save=False
    ).get_hydrated_version()

    step = Step.parse_obj(
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
    assert artifact.dict() == artifact_response.dict()
