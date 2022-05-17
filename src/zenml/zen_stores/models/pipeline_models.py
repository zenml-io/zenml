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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import UUID

from pydantic import BaseModel, Field

import zenml
from zenml.logger import get_logger
from zenml.zen_stores.models import StackWrapper

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.steps import BaseStep

logger = get_logger(__name__)


def get_git_sha(clean: bool = True) -> Optional[str]:
    """Returns the current git HEAD SHA.

    If the current working directory is not inside a git repo, this will return
    `None`.

    Args:
        clean: If `True` and there any untracked files or files in the index or
            working tree, this function will return `None`.
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


class StepWrapper(BaseModel):
    """Pydantic object representing a step.

    Attributes:
        name: Step name
        docstring: Docstring of the step
    """

    name: str
    docstring: Optional[str]

    @classmethod
    def from_step(cls, step: "BaseStep") -> "StepWrapper":
        """Creates a StepWrapper from a step instance."""
        return cls(
            name=step.name,
            docstring=step.__doc__,
        )


class PipelineWrapper(BaseModel):
    """Pydantic object representing a pipeline.

    Attributes:
        name: Pipeline name
        docstring: Docstring of the pipeline
        steps: List of steps in this pipeline
    """

    name: str
    docstring: Optional[str]
    steps: List[StepWrapper]

    @classmethod
    def from_pipeline(cls, pipeline: "BasePipeline") -> "PipelineWrapper":
        """Creates a PipelineWrapper from a pipeline instance."""
        steps = [
            StepWrapper.from_step(step) for step in pipeline.steps.values()
        ]

        return cls(
            name=pipeline.name,
            docstring=pipeline.__doc__,
            steps=steps,
        )


class PipelineRunWrapper(BaseModel):
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
        user_id: Id of the user that ran this pipeline.
        project_name: Name of the project that this pipeline was run in.
    """

    name: str
    zenml_version: str = zenml.__version__
    git_sha: Optional[str] = Field(default_factory=get_git_sha)

    pipeline: PipelineWrapper
    stack: StackWrapper
    runtime_configuration: Dict[str, Any]

    user_id: UUID
    project_name: Optional[str]
