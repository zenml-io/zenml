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

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import pytest

from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus
from zenml.exceptions import InputResolutionError
from zenml.models import (
    ArtifactResponseModel,
    ProjectResponseModel,
    StepRunResponseModel,
    UserResponseModel,
)
from zenml.orchestrators import input_utils


def _create_step_run(
    user: UserResponseModel,
    project: ProjectResponseModel,
    step_name: str,
    output_artifacts: Optional[Dict[str, ArtifactResponseModel]] = None,
):
    """Creates a step run with the given user, project, step name and output
    artifacts."""
    step = Step.parse_obj(
        {
            "spec": {"source": "", "upstream_steps": [], "inputs": {}},
            "config": {"name": step_name, "enable_cache": True},
        }
    )

    return StepRunResponseModel(
        id=uuid4(),
        name="sample_step",
        pipeline_run_id=uuid4(),
        step=step,
        status=ExecutionStatus.COMPLETED,
        created=datetime.now(),
        updated=datetime.now(),
        project=project,
        user=user,
        output_artifacts=output_artifacts or {},
    )


def test_input_resolution(
    mocker, sample_user_model, sample_project_model, sample_artifact_model
):
    """Tests that input resolution works if the correct models exist in the
    zen store."""
    step_run = _create_step_run(
        user=sample_user_model,
        project=sample_project_model,
        step_name="upstream_step",
        output_artifacts={"output_name": sample_artifact_model},
    )

    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=[step_run],
    )
    step = Step.parse_obj(
        {
            "spec": {
                "source": "",
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
        step=step, run_id=uuid4()
    )
    assert input_artifacts == {"input_name": sample_artifact_model}
    assert parent_ids == [step_run.id]


def test_input_resolution_with_missing_step_run(mocker):
    """Tests that input resolution fails if the upstream step run is missing."""
    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=[],
    )
    step = Step.parse_obj(
        {
            "spec": {
                "source": "",
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
        input_utils.resolve_step_inputs(step=step, run_id=uuid4())


def test_input_resolution_with_missing_artifact(
    mocker, sample_user_model, sample_project_model
):
    """Tests that input resolution fails if the upstream step run output
    artifact is missing."""
    step_run = _create_step_run(
        user=sample_user_model,
        project=sample_project_model,
        step_name="upstream_step",
    )

    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=[step_run],
    )
    step = Step.parse_obj(
        {
            "spec": {
                "source": "",
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
        input_utils.resolve_step_inputs(step=step, run_id=uuid4())
