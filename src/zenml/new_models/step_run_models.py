from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)

# -------- #
# RESPONSE #
# -------- #


class StepRunResponseModel(ProjectScopedResponseModel):
    """Domain Model representing a step in a pipeline run."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    pipeline_run_id: UUID
    parent_step_ids: List[UUID]

    entrypoint_name: str
    parameters: Dict[str, str]
    step_configuration: Dict[str, Any]
    docstring: str

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: int
    mlmd_parent_step_ids: List[int]


# ------- #
# REQUEST #
# ------- #


class StepRunRequestModel(ProjectScopedRequestModel):
    """Domain Model representing a step in a pipeline run."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    pipeline_run_id: UUID
    parent_step_ids: List[UUID]

    entrypoint_name: str
    parameters: Dict[str, str]
    step_configuration: Dict[str, Any]
    docstring: Optional[str]

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: int
    mlmd_parent_step_ids: List[int]
