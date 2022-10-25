from typing import List, Optional

from pydantic import Field

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin
from zenml.new_models.pipeline_run_models import RunResponseModel
# -------- #
# RESPONSE #
# -------- #


class PipelineResponseModel(
    ProjectScopedResponseModel, AnalyticsTrackedModelMixin
):
    """Pipeline model with User and Project fully hydrated."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    spec: PipelineSpec

    runs: Optional[List["RunResponseModel"]] = Field(
        title="A list of the last x Pipeline Runs."
    )
    status: List[ExecutionStatus] = Field(
        title="The status of the last x Pipeline Runs."
    )


# ------- #
# REQUEST #
# ------- #


class PipelineRequestModel(
    ProjectScopedRequestModel, AnalyticsTrackedModelMixin
):
    """Domain model representing a pipeline."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    spec: PipelineSpec
