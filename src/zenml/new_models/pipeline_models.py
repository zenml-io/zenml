from typing import List, Optional

from pydantic import BaseModel, Field

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.new_models.pipeline_run_models import PipelineRunResponseModel
from zenml.new_models.base_models import update

# ---- #
# BASE #
# ---- #
class PipelineBaseModel(BaseModel):
    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    spec: PipelineSpec


# -------- #
# RESPONSE #
# -------- #


class PipelineResponseModel(PipelineBaseModel, ProjectScopedResponseModel):
    """Pipeline model with User and Project fully hydrated."""

    runs: Optional[List["PipelineRunResponseModel"]] = Field(
        title="A list of the last x Pipeline Runs."
    )
    status: List[ExecutionStatus] = Field(
        title="The status of the last x Pipeline Runs."
    )


# ------- #
# REQUEST #
# ------- #


class PipelineRequestModel(PipelineBaseModel, ProjectScopedRequestModel):
    """Domain model representing a pipeline."""



# ------ #
# UPDATE #
# ------ #

@update
class PipelineUpdateModel(PipelineRequestModel):
    """"""