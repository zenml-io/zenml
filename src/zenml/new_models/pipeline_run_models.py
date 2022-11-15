from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import UUID

from pydantic import BaseModel, Field

from zenml import __version__ as current_zenml_version
from zenml.enums import ExecutionStatus
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.new_models.base_models import update

if TYPE_CHECKING:
    from zenml.new_models import PipelineResponseModel, StackResponseModel


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
    name: str = Field(
        title="The name of the pipeline run.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    pipeline_configuration: Dict[str, Any]
    num_steps: int
    zenml_version: Optional[str] = current_zenml_version
    git_sha: Optional[str] = Field(default_factory=get_git_sha)

    # ID in MLMD - needed for some metadata store methods.
    mlmd_id: Optional[int]  # Modeled as Optional, so we can remove it later.


# -------- #
# RESPONSE #
# -------- #


class PipelineRunResponseModel(
    PipelineRunBaseModel, ProjectScopedResponseModel
):
    """Pipeline model with User and Project fully hydrated."""

    status: ExecutionStatus = Field(title="The status of the run.")

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
    """Domain Model representing a pipeline run."""

    stack: Optional[UUID]  # Might become None if the stack is deleted.
    pipeline: Optional[UUID]  # Unlisted runs have this as None.


# ------ #
# UPDATE #
# ------ #

@update
class PipelineRunUpdateModel(PipelineRunRequestModel):
    """"""
