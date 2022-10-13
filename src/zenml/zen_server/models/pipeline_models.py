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
"""Project Models for the API endpoint definitions."""
from typing import List, Optional

from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineModel,
    PipelineRunModel,
    ProjectModel,
    StackModel,
    UserModel,
)
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.zen_server.models.base_models import (
    ProjectScopedCreateRequest,
    UpdateRequest,
)


class CreatePipelineRequest(ProjectScopedCreateRequest[PipelineModel]):
    """Pipeline model for create requests."""

    _MODEL_TYPE = PipelineModel

    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    spec: PipelineSpec


class UpdatePipelineRequest(UpdateRequest[PipelineModel]):
    """Pipeline model for update requests."""

    _MODEL_TYPE = PipelineModel

    name: Optional[str] = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    spec: PipelineSpec


class HydratedPipelineModel(PipelineModel):
    """Pipeline model with User and Project fully hydrated."""

    runs: List["PipelineRunModel"] = Field(
        title="A list of the last x Pipeline Runs."
    )
    status: List[ExecutionStatus] = Field(
        title="The status of the last x Pipeline Runs."
    )
    project: ProjectModel = Field(  # type: ignore[assignment]
        title="The project that contains this pipeline."
    )
    user: UserModel = Field(  # type: ignore[assignment]
        title="The user that created this pipeline.",
    )

    @classmethod
    def from_model(
        cls, pipeline_model: PipelineModel, num_runs: int = 3
    ) -> "HydratedPipelineModel":
        """Converts this model to a hydrated model.

        Args:
            pipeline_model: The pipeline model to hydrate.
            num_runs: The number of runs to include.

        Returns:
            A hydrated model.
        """
        zen_store = GlobalConfiguration().zen_store

        project = zen_store.get_project(pipeline_model.project)
        user = zen_store.get_user(pipeline_model.user)
        runs = zen_store.list_runs(pipeline_id=pipeline_model.id)
        last_x_runs = runs[:num_runs]
        status_last_x_runs = []
        for run in last_x_runs:
            status_last_x_runs.append(zen_store.get_run_status(run_id=run.id))

        return cls(
            id=pipeline_model.id,
            name=pipeline_model.name,
            project=project,
            user=user,
            runs=last_x_runs,
            status=status_last_x_runs,
            docstring=pipeline_model.docstring,
            spec=pipeline_model.spec,
            created=pipeline_model.created,
            updated=pipeline_model.updated,
        )


class HydratedPipelineRunModel(PipelineRunModel):
    """Pipeline model with User and Project fully hydrated."""

    pipeline: Optional[PipelineModel] = Field(
        title="The pipeline this run belongs to."
    )
    stack: Optional[StackModel] = Field(
        title="The stack that was used for this run."
    )
    user: UserModel = Field(  # type: ignore[assignment]
        title="The user that ran this pipeline.",
    )
    status: ExecutionStatus = Field(title="The status of the run.")

    @classmethod
    def from_model(
        cls,
        run_model: PipelineRunModel,
    ) -> "HydratedPipelineRunModel":
        """Converts this model to a hydrated model.

        Args:
            run_model: The run model to hydrate.

        Returns:
            A hydrated model.
        """
        zen_store = GlobalConfiguration().zen_store

        status = zen_store.get_run_status(run_id=run_model.id)

        pipeline = None
        stack = None
        user = None

        if run_model.pipeline_id:
            pipeline = zen_store.get_pipeline(run_model.pipeline_id)
        if run_model.stack_id:
            stack = zen_store.get_stack(run_model.stack_id)
        if run_model.user:
            user = zen_store.get_user(run_model.user)

        return cls(
            **run_model.dict(exclude={"user", "pipeline", "stack"}),
            pipeline=pipeline,
            stack=stack,
            user=user,
            status=status
        )
