#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


import pytest

from zenml.config.step_configurations import Step
from zenml.enums import StepRunInputArtifactType
from zenml.exceptions import InputResolutionError
from zenml.models import Page
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators import input_utils


def test_input_resolution(
    mocker,
    sample_artifact_version_model: ArtifactVersionResponse,
    create_step_run,
    sample_pipeline_run,
):
    """Tests that input resolution works if the correct models exist in the
    zen store."""
    step_run = create_step_run(
        step_run_name="upstream_step",
        output_artifacts={"output_name": [sample_artifact_version_model]},
    )

    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=Page(
            index=1, max_size=50, total_pages=1, total=1, items=[step_run]
        ),
    )
    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": ["upstream_step"],
                "inputs": {
                    "input_name": {
                        "step_name": "upstream_step",
                        "output_name": "output_name",
                    }
                },
            },
            "config": {"name": "step_name", "enable_cache": True},
        }
    )

    input_artifacts, parent_ids = input_utils.resolve_step_inputs(
        step=step, pipeline_run=sample_pipeline_run
    )
    assert input_artifacts == {
        "input_name": StepRunInputResponse(
            input_type=StepRunInputArtifactType.STEP_OUTPUT,
            **sample_artifact_version_model.model_dump(),
        )
    }
    assert parent_ids == [step_run.id]


def test_input_resolution_with_missing_step_run(mocker, sample_pipeline_run):
    """Tests that input resolution fails if the upstream step run is missing."""
    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=Page(
            index=1, max_size=50, total_pages=1, total=0, items=[]
        ),
    )
    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {
                    "input_name": {
                        "step_name": "non_existent",
                        "output_name": "",
                    }
                },
            },
            "config": {"name": "step_name", "enable_cache": True},
        }
    )

    with pytest.raises(InputResolutionError):
        input_utils.resolve_step_inputs(
            step=step, pipeline_run=sample_pipeline_run
        )


def test_input_resolution_with_missing_artifact(
    mocker, create_step_run, sample_pipeline_run
):
    """Tests that input resolution fails if the upstream step run output
    artifact is missing."""
    step_run = create_step_run(
        step_name="upstream_step",
    )

    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=Page(
            index=1, max_size=50, total_pages=1, total=1, items=[step_run]
        ),
    )
    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {
                    "input_name": {
                        "step_name": "upstream_step",
                        "output_name": "non_existent",
                    }
                },
            },
            "config": {"name": "step_name", "enable_cache": True},
        }
    )

    with pytest.raises(InputResolutionError):
        input_utils.resolve_step_inputs(
            step=step, pipeline_run=sample_pipeline_run
        )


def test_input_resolution_fetches_all_run_steps(
    mocker, sample_artifact_version_model, create_step_run, sample_pipeline_run
):
    """Tests that input resolution fetches all step runs of the pipeline run."""
    step_run = create_step_run(
        step_run_name="upstream_step",
        output_artifacts={"output_name": [sample_artifact_version_model]},
    )
    second_step_run = create_step_run(
        step_run_name="other_step",
    )
    return_values = [
        Page(index=1, max_size=1, total_pages=2, total=2, items=[step_run]),
        Page(
            index=2,
            max_size=1,
            total_pages=2,
            total=2,
            items=[second_step_run],
        ),
    ]
    mock_list_run_steps = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        side_effect=return_values,
    )
    step = Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": ["upstream_step"],
                "inputs": {
                    "input_name": {
                        "step_name": "upstream_step",
                        "output_name": "output_name",
                    }
                },
            },
            "config": {"name": "step_name", "enable_cache": True},
        }
    )

    input_utils.resolve_step_inputs(
        step=step, pipeline_run=sample_pipeline_run
    )

    # `resolve_step_inputs(...)` depaginates the run steps so we fetch all
    # step runs for the pipeline run
    assert mock_list_run_steps.call_count == 2
