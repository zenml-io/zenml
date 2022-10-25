from typing import Any, Dict, Optional, cast
from uuid import UUID

from pydantic import Field

from zenml import __version__ as current_zenml_version
from zenml.enums import ExecutionStatus
from zenml.models import PipelineModel, StackModel
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
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


# -------- #
# RESPONSE #
# -------- #


class RunResponseModel(ProjectScopedResponseModel, AnalyticsTrackedModelMixin):
    """Pipeline model with User and Project fully hydrated."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    pipeline: Optional[PipelineModel] = Field(
        title="The pipeline this run belongs to."
    )
    stack: Optional[StackModel] = Field(
        title="The stack that was used for this run."
    )

    pipeline_configuration: Dict[str, Any]
    num_steps: int
    zenml_version: str = Field(title="")  # TODO
    git_sha: str = Field(title="")  # TODO

    status: ExecutionStatus = Field(title="The status of the run.")

    mlmd_id: Optional[int]  # Modeled as Optional, so we can remove it later.


# ------- #
# REQUEST #
# ------- #


class RunRequestModel(ProjectScopedRequestModel, AnalyticsTrackedModelMixin):
    """Domain Model representing a pipeline run."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    stack: Optional[UUID]  # Might become None if the stack is deleted.
    pipeline: Optional[UUID]  # Unlisted runs have this as None.

    pipeline_configuration: Dict[str, Any]
    num_steps: int
    zenml_version: Optional[str] = current_zenml_version
    git_sha: Optional[str] = Field(default_factory=get_git_sha)

    # ID in MLMD - needed for some metadata store methods.
    mlmd_id: Optional[int]  # Modeled as Optional, so we can remove it later.
