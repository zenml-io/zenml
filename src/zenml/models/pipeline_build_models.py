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
"""Models representing pipeline builds."""

from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.build_configuration import PipelineBuild
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.filter_models import WorkspaceScopedFilterModel

if TYPE_CHECKING:
    from zenml.models.pipeline_models import PipelineResponseModel
    from zenml.models.stack_models import StackResponseModel

# ---- #
# BASE #
# ---- #


class PipelineBuildBaseModel(BaseModel):
    """Base model for pipeline builds."""

    configuration: PipelineBuild


# -------- #
# RESPONSE #
# -------- #


class PipelineBuildResponseModel(
    PipelineBuildBaseModel, WorkspaceScopedResponseModel
):
    """Response model for pipeline builds."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        title="The pipeline this build belongs to."
    )
    stack: Optional["StackResponseModel"] = Field(
        title="The stack that was used for this build."
    )


# ------ #
# FILTER #
# ------ #


class PipelineBuildFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all pipeline builds."""

    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace for this pipeline build."
    )
    user_id: Union[UUID, str] = Field(
        default=None, description="User that produced this pipeline build."
    )
    pipeline_id: Union[UUID, str] = Field(
        default=None,
        description="Pipeline associated with the pipeline build.",
    )
    stack_id: Union[UUID, str] = Field(
        default=None, description="Stack used for the Pipeline Run"
    )


# ------- #
# REQUEST #
# ------- #


class PipelineBuildRequestModel(
    PipelineBuildBaseModel, WorkspaceScopedRequestModel
):
    """Request model for pipelines builds."""

    stack: Optional[UUID] = None
    pipeline: Optional[UUID] = None
