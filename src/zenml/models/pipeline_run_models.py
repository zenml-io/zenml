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
from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import UUID

from pydantic import BaseModel, Field

from zenml import __version__ as current_zenml_version
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH

if TYPE_CHECKING:
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
