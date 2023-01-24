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
    cast,
)
from uuid import UUID

from pydantic import BaseModel, Field

from zenml import __version__ as current_zenml_version
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import ProjectScopedFilterModel

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
    from sqlmodel import SQLModel

    from zenml.models.pipeline_models import PipelineResponseModel
    from zenml.models.stack_models import StackResponseModel


def get_git_sha(clean: bool = True) -> Optional[str]:
    """Returns the current git HEAD SHA.

    If the current working directory is not inside a git repo, this will return
    `None`.

    Args:
        clean: If `True` and there any untracked files or files in the index or
            working tree, this function will return `None`.

    Returns:
        The current git HEAD SHA or `None` if the current working directory is
        not inside a git repo.
    """
    try:
        from git.exc import InvalidGitRepositoryError
        from git.repo.base import Repo
    except ImportError:
        return None

    try:
        repo = Repo(search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None

    if clean and repo.is_dirty(untracked_files=True):
        return None
    return cast(str, repo.head.object.hexsha)


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
    schedule_id: Optional[UUID]
    enable_cache: Optional[bool]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: ExecutionStatus
    pipeline_configuration: Dict[str, Any]
    num_steps: Optional[int]
    zenml_version: Optional[str] = Field(
        title="ZenML version.",
        default=current_zenml_version,
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
    git_sha: Optional[str] = Field(
        default_factory=get_git_sha, max_length=STR_FIELD_MAX_LENGTH
    )


# -------- #
# RESPONSE #
# -------- #


class PipelineRunResponseModel(
    PipelineRunBaseModel, ProjectScopedResponseModel
):
    """Pipeline run model with user, project, pipeline, and stack hydrated."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        title="The pipeline this run belongs to."
    )
    stack: Optional["StackResponseModel"] = Field(
        title="The stack that was used for this run."
    )


# ------ #
# FILTER #
# ------ #


class PipelineRunFilterModel(ProjectScopedFilterModel):
    """Model to enable advanced filtering of all Projects."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "unlisted",
    ]

    name: str = Field(
        default=None,
        description="Name of the Pipeline Run",
    )
    orchestrator_run_id: str = Field(
        default=None,
        description="Name of the Pipeline Run within the orchestrator",
    )

    pipeline_id: Union[UUID, str] = Field(
        default=None, description="Pipeline associated with the Pipeline"
    )
    project_id: Union[UUID, str] = Field(
        default=None, description="Project of the Pipeline"
    )
    user_id: Union[UUID, str] = Field(None, description="User of the Pipeline")

    stack_id: Union[UUID, str] = Field(
        default=None, description="Stack used for the Pipeline Run"
    )
    schedule_id: Union[UUID, str] = Field(
        default=None, description="Schedule that triggered the Pipeline Run"
    )

    status: str = Field(
        default=None,
        description="Name of the Pipeline Run",
    )
    start_time: Union[datetime, str] = Field(
        default=None, description="Start time for this run"
    )
    end_time: Union[datetime, str] = Field(
        default=None, description="End time for this run"
    )

    num_steps: int = Field(
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

        base_filter = super().generate_filter(table)

        if self.unlisted is not None:
            if self.unlisted is True:
                unlisted_filter = getattr(table, "pipeline_id").is_(None)
            else:
                unlisted_filter = getattr(table, "pipeline_id").is_not(None)

            # TODO: make this right
            # This needs to be an AND right now to work with the project
            # scoping of the superclass
            return and_(base_filter, unlisted_filter)

        return base_filter


# ------- #
# REQUEST #
# ------- #


class PipelineRunRequestModel(PipelineRunBaseModel, ProjectScopedRequestModel):
    """Pipeline run model with user, project, pipeline, and stack as UUIDs."""

    id: UUID
    stack: Optional[UUID]  # Might become None if the stack is deleted.
    pipeline: Optional[UUID]  # Unlisted runs have this as None.


# ------ #
# UPDATE #
# ------ #


class PipelineRunUpdateModel(BaseModel):
    """Pipeline run update model."""

    status: Optional[ExecutionStatus] = None
    end_time: Optional[datetime] = None
