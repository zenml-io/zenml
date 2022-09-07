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
"""Pipeline models implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from pydantic import BaseModel, Field

from zenml import __version__ as current_zenml_version
from zenml.enums import ArtifactType


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


class PipelineModel(BaseModel):
    """Pydantic object representing a pipeline.

    Attributes:
        name: Pipeline name
        docstring: Docstring of the pipeline
        steps: List of steps in this pipeline
    """

    id: Optional[UUID]
    name: str

    project_id: UUID
    owner: UUID

    docstring: Optional[str]
    configuration: Dict[str, str]

    created_at: Optional[datetime]


class PipelineRunModel(BaseModel):
    """Pydantic object representing a pipeline run.

    Attributes:
        name: Pipeline run name.
        zenml_version: Version of ZenML that this pipeline run was performed
            with.
        git_sha: Git commit SHA that this pipeline run was performed on. This
            will only be set if the pipeline code is in a git repository and
            there are no uncommitted files when running the pipeline.
        pipeline: Pipeline that this run is referring to.
        stack: Stack that this run was performed on.
        runtime_configuration: Runtime configuration that was used for this run.
        owner: Id of the user that ran this pipeline.
    """

    id: Optional[UUID]  # ID in our DB
    mlmd_id: Optional[int]  # ID in MLMD
    name: str

    owner: Optional[UUID]  # might not be set for scheduled runs
    stack_id: Optional[UUID]  # might not be set for scheduled runs
    pipeline_id: Optional[UUID]  # might not be set for scheduled runs

    runtime_configuration: Optional[Dict[str, Any]]

    zenml_version: Optional[str] = current_zenml_version
    git_sha: Optional[str] = Field(default_factory=get_git_sha)
    created_at: Optional[datetime]


class StepRunModel(BaseModel):
    """Pydantic object representing a step of a pipeline run."""

    mlmd_id: int  # ID in MLMD
    name: str
    pipeline_run_id: Optional[UUID]  # TODO: make required
    parent_step_ids: List[int]  # ID in MLMD
    docstring: Optional[str]
    entrypoint_name: str


class ArtifactModel(BaseModel):
    """Pydantic object representing an artifact."""

    mlmd_id: int  # ID in MLMD
    type: ArtifactType
    uri: str
    materializer: str
    data_type: str
    parent_step_id: int  # ID in MLMD
    producer_step_id: int  # ID in MLMD
    is_cached: bool
