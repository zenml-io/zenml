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
"""Models representing pipelines."""

from typing import Any, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.pipeline_spec import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.pipeline_run_models import PipelineRunResponseModel

# ---- #
# BASE #
# ---- #


class PipelineBaseModel(BaseModel):
    """Base model for pipelines."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    version: str = Field(
        title="The version of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    version_hash: str = Field(
        title="The version hash of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docstring: Optional[str] = Field(
        title="The docstring of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    spec: PipelineSpec = Field(title="The spec of the pipeline.")


# -------- #
# RESPONSE #
# -------- #


class PipelineResponseModel(PipelineBaseModel, WorkspaceScopedResponseModel):
    """Pipeline response model user, workspace, runs, and status hydrated."""

    status: Optional[List[ExecutionStatus]] = Field(
        default=None, title="The status of the last 3 Pipeline Runs."
    )

    def get_runs(self, **kwargs: Any) -> List["PipelineRunResponseModel"]:
        """Get runs of this pipeline.

        Can be used to fetch runs other than `self.runs` and supports
        fine-grained filtering and pagination.

        Args:
            **kwargs: Further arguments for filtering or pagination that are
                passed to `client.list_pipeline_runs()`.

        Returns:
            List of runs of this pipeline.
        """
        from zenml.client import Client

        return Client().list_pipeline_runs(pipeline_id=self.id, **kwargs).items

    @property
    def runs(self) -> List["PipelineRunResponseModel"]:
        """Returns the 20 most recent runs of this pipeline in descending order.

        Returns:
            The 20 most recent runs of this pipeline in descending order.
        """
        return self.get_runs()

    @property
    def num_runs(self) -> int:
        """Returns the number of runs of this pipeline.

        Returns:
            The number of runs of this pipeline.
        """
        from zenml.client import Client

        return Client().list_pipeline_runs(pipeline_id=self.id, size=1).total

    @property
    def last_run(self) -> "PipelineRunResponseModel":
        """Returns the last run of this pipeline.

        Returns:
            The last run of this pipeline.

        Raises:
            RuntimeError: If no runs were found for this pipeline.
        """
        runs = self.get_runs(size=1)
        if not runs:
            raise RuntimeError(
                f"No runs found for pipeline '{self.name}' with id {self.id}."
            )
        return runs[0]

    @property
    def last_successful_run(self) -> "PipelineRunResponseModel":
        """Returns the last successful run of this pipeline.

        Returns:
            The last successful run of this pipeline.

        Raises:
            RuntimeError: If no successful runs were found for this pipeline.
        """
        runs = self.get_runs(status=ExecutionStatus.COMPLETED, size=1)
        if not runs:
            raise RuntimeError(
                f"No successful runs found for pipeline '{self.name}' with id "
                f"{self.id}."
            )
        return runs[0]


# ------ #
# FILTER #
# ------ #


class PipelineFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Workspaces."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline",
    )
    version: Optional[str] = Field(
        default=None,
        description="Version of the Pipeline",
    )
    version_hash: Optional[str] = Field(
        default=None,
        description="Version hash of the Pipeline",
    )
    docstring: Optional[str] = Field(
        default=None,
        description="Docstring of the Pipeline",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Pipeline"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User of the Pipeline"
    )


# ------- #
# REQUEST #
# ------- #


class PipelineRequestModel(PipelineBaseModel, WorkspaceScopedRequestModel):
    """Pipeline request model."""


# ------ #
# UPDATE #
# ------ #


@update_model
class PipelineUpdateModel(PipelineRequestModel):
    """Pipeline update model."""
