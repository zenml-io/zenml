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
"""Model definitions for pipelines, runs, steps, and artifacts."""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml import __version__ as current_zenml_version
from zenml.enums import ArtifactType
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


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


class PipelineModel(AnalyticsTrackedModelMixin):
    """Domain model representing a pipeline."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["id", "project", "user"]

    id: UUID = Field(
        default_factory=uuid4, title="The unique id of the pipeline."
    )
    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    configuration: Dict[str, str]

    project: UUID = Field(title="The project that contains this pipeline.")
    user: UUID = Field(
        title="The id of the user that created this pipeline.",
    )

    creation_date: datetime = Field(
        default_factory=datetime.now,
        title="The time at which the pipeline was created.",
    )


class PipelineRunModel(AnalyticsTrackedModelMixin):
    """Domain Model representing a pipeline run."""

    id: UUID = Field(
        default_factory=uuid4, title="The unique id of the pipeline run."
    )

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    stack_id: Optional[UUID]  # might not be set for scheduled runs
    pipeline_id: Optional[UUID]  # might not be set for scheduled runs

    runtime_configuration: Optional[Dict[str, Any]]

    zenml_version: Optional[str] = current_zenml_version
    git_sha: Optional[str] = Field(default_factory=get_git_sha)

    # ID in MLMD - needed for some metadata store methods
    mlmd_id: Optional[int]
    user: Optional[UUID]  # might not be set for scheduled runs

    creation_date: datetime = Field(
        default_factory=datetime.now,
        title="The time at which the run was registered.",
    )


class StepRunModel(BaseModel):
    """Pydantic object representing a step of a pipeline run."""

    id: Optional[UUID]
    name: str

    pipeline_run_id: Optional[UUID]
    parent_step_ids: Optional[List[UUID]]

    docstring: Optional[str]
    parameters: Dict[str, str]
    entrypoint_name: str

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: int
    mlmd_parent_step_ids: List[int]


class ArtifactModel(BaseModel):
    """Pydantic object representing an artifact."""

    id: Optional[UUID]
    name: Optional[str]  # Name of the output in the parent step

    parent_step_id: Optional[UUID]
    producer_step_id: Optional[UUID]

    type: ArtifactType
    uri: str
    materializer: str
    data_type: str
    is_cached: bool

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: int
    mlmd_parent_step_id: int
    mlmd_producer_step_id: int
