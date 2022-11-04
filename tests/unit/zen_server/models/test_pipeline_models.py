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

from uuid import UUID

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunModel, ProjectModel, UserModel
from zenml.zen_server.models.pipeline_models import (
    HydratedPipelineModel,
    PipelineModel,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _create_run_model(
    name: str, user_id: UUID, project_id: UUID
) -> PipelineRunModel:
    """Creates a pipeline run model with the given attributes."""
    return PipelineRunModel(
        user=user_id,
        project=project_id,
        name=name,
        num_steps=1,
        pipeline_configuration={},
        status=ExecutionStatus.COMPLETED,
    )


def test_pipeline_model_hydration(mocker):
    """Tests that pipeline model hydration works as expected."""

    user = UserModel()
    project = ProjectModel(name="my_project")
    runs = [
        _create_run_model(name="run_0", user_id=user.id, project_id=project.id),
        _create_run_model(name="run_1", user_id=user.id, project_id=project.id),
        _create_run_model(name="run_2", user_id=user.id, project_id=project.id),
        _create_run_model(name="run_3", user_id=user.id, project_id=project.id),
    ]

    mocker.patch.object(
        SqlZenStore,
        "get_user",
        return_value=user,
    )
    mocker.patch.object(
        SqlZenStore,
        "get_project",
        return_value=project,
    )
    mocker.patch.object(
        SqlZenStore,
        "list_runs",
        return_value=runs,
    )
    mocker.patch.object(
        SqlZenStore,
        "get_run",
        return_value=runs[0],
    )
    model = PipelineModel(
        user=user.id,
        project=project.id,
        name="my_pipeline",
        spec=PipelineSpec(steps=[]),
    )

    hydrated_model = HydratedPipelineModel.from_model(model)
    assert hydrated_model.runs == runs[-3:]
