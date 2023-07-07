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
"""Models representing pipeline runs."""

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field

from zenml import __version__ as current_zenml_version
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.enums import ExecutionStatus, LogicalOperators
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
    from sqlmodel import SQLModel

    from zenml.models import (
        ArtifactResponseModel,
        PipelineBuildResponseModel,
        PipelineDeploymentResponseModel,
        PipelineResponseModel,
        RunMetadataResponseModel,
        StackResponseModel,
        StepRunResponseModel,
    )

# ---- #
# BASE #
# ---- #


class PipelineRunBaseModel(BaseModel):
    """Base model for pipeline runs."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    orchestrator_run_id: Optional[str] = Field(
        title="The orchestrator run ID.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    schedule_id: Optional[UUID] = Field(
        title="The ID of the schedule that triggered this pipeline run.",
        default=None,
    )
    enable_cache: Optional[bool] = Field(
        title="Whether to enable caching for this pipeline run.",
        default=None,
    )
    start_time: Optional[datetime] = Field(
        title="The start time of the pipeline run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the pipeline run.",
        default=None,
    )
    status: ExecutionStatus = Field(
        title="The status of the pipeline run.",
    )
    config: PipelineConfiguration = Field(
        title="The pipeline configuration used for this pipeline run.",
    )
    num_steps: Optional[int] = Field(
        title="The number of steps in this pipeline run.",
        default=None,
    )
    client_version: Optional[str] = Field(
        title="Client version.",
        default=current_zenml_version,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    server_version: Optional[str] = Field(
        title="Server version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    client_environment: Dict[str, str] = Field(
        default={},
        title=(
            "Environment of the client that initiated this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )
    orchestrator_environment: Dict[str, str] = Field(
        default={},
        title=(
            "Environment of the orchestrator that executed this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )


# -------- #
# RESPONSE #
# -------- #


class PipelineRunResponseModel(
    PipelineRunBaseModel, WorkspaceScopedResponseModel
):
    """Pipeline run model with user, workspace, pipeline, and stack hydrated."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        default=None, title="The pipeline this run belongs to."
    )
    stack: Optional["StackResponseModel"] = Field(
        default=None, title="The stack that was used for this run."
    )
    metadata: Dict[str, "RunMetadataResponseModel"] = Field(
        default={},
        title="Metadata associated with this pipeline run.",
    )
    build: Optional["PipelineBuildResponseModel"] = Field(
        default=None, title="The pipeline build that was used for this run."
    )
    deployment: Optional["PipelineDeploymentResponseModel"] = Field(
        default=None, title="The deployment that was used for this run."
    )
    steps: Dict[str, "StepRunResponseModel"] = Field(
        default={}, title="The steps of this run."
    )

    @property
    def artifacts(self) -> List["ArtifactResponseModel"]:
        """Get all artifacts that are outputs of steps of this pipeline run.

        Returns:
            All output artifacts of this pipeline run (including cached ones).
        """
        from zenml.utils.artifact_utils import get_artifacts_of_pipeline_run

        return get_artifacts_of_pipeline_run(self)

    @property
    def produced_artifacts(self) -> List["ArtifactResponseModel"]:
        """Get all artifacts produced during this pipeline run.

        Returns:
            A list of all artifacts produced during this pipeline run.
        """
        from zenml.utils.artifact_utils import get_artifacts_of_pipeline_run

        return get_artifacts_of_pipeline_run(self, only_produced=True)

    def get_step(self, step: str) -> "StepRunResponseModel":
        """(Deprecated) Get a step by name.

        Args:
            step: Name of the step to get.

        Returns:
            The step with the given name.
        """
        from zenml.logger import get_logger

        logger = get_logger(__name__)
        logger.warning(
            "`run.get_step(<step_name>)` is deprecated and will be removed in "
            "a future release. Please use `run.steps[<step_name>]` instead."
        )
        return self.steps[step]


# ------ #
# FILTER #
# ------ #


class PipelineRunFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Workspaces."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "unlisted",
        "code_repository_id",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline Run",
    )
    orchestrator_run_id: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline Run within the orchestrator",
    )

    pipeline_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Pipeline associated with the Pipeline Run"
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Pipeline Run"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User that created the Pipeline Run"
    )

    stack_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Stack used for the Pipeline Run"
    )
    schedule_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Schedule that triggered the Pipeline Run"
    )
    build_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Build used for the Pipeline Run"
    )
    deployment_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Deployment used for the Pipeline Run"
    )
    code_repository_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Code repository used for the Pipeline Run"
    )

    status: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline Run",
    )
    start_time: Optional[Union[datetime, str]] = Field(
        default=None, description="Start time for this run"
    )
    end_time: Optional[Union[datetime, str]] = Field(
        default=None, description="End time for this run"
    )

    num_steps: Optional[int] = Field(
        default=None,
        description="Amount of steps in the Pipeline Run",
    )

    unlisted: Optional[bool] = None

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the filter for the query.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlalchemy import and_
        from sqlmodel import or_

        base_filter = super().generate_filter(table)

        operator = (
            or_ if self.logical_operator == LogicalOperators.OR else and_
        )

        if self.unlisted is not None:
            if self.unlisted is True:
                unlisted_filter = getattr(table, "pipeline_id").is_(None)
            else:
                unlisted_filter = getattr(table, "pipeline_id").is_not(None)

            base_filter = operator(base_filter, unlisted_filter)

        if self.code_repository_id:
            from zenml.zen_stores.schemas import (
                CodeReferenceSchema,
                PipelineDeploymentSchema,
                PipelineRunSchema,
            )

            code_repo_filter = and_(  # type: ignore[type-var]
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.code_reference_id
                == CodeReferenceSchema.id,
                CodeReferenceSchema.code_repository_id
                == self.code_repository_id,
            )

            base_filter = operator(base_filter, code_repo_filter)

        return base_filter


# ------- #
# REQUEST #
# ------- #


class PipelineRunRequestModel(
    PipelineRunBaseModel, WorkspaceScopedRequestModel
):
    """Pipeline run model with user, workspace, pipeline, and stack as UUIDs."""

    id: UUID
    stack: Optional[UUID]  # Might become None if the stack is deleted.
    pipeline: Optional[UUID]  # Unlisted runs have this as None.
    build: Optional[UUID]
    deployment: Optional[UUID]


# ------ #
# UPDATE #
# ------ #


class PipelineRunUpdateModel(BaseModel):
    """Pipeline run update model."""

    status: Optional[ExecutionStatus] = None
    end_time: Optional[datetime] = None
