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
"""Models representing pipeline build outputs."""

from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.build_configuration import BuildOutput
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


class BuildOutputBaseModel(BaseModel):
    """Base model for build outputs."""

    configuration: BuildOutput


# -------- #
# RESPONSE #
# -------- #


class BuildOutputResponseModel(
    BuildOutputBaseModel, WorkspaceScopedResponseModel
):
    """Response model for build outputs."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        title="The pipeline this build belongs to."
    )
    stack: Optional["StackResponseModel"] = Field(
        title="The stack that was used for this build."
    )


# ------ #
# FILTER #
# ------ #


class BuildOutputFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all build outputs."""

    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace for this build output."
    )
    user_id: Union[UUID, str] = Field(
        default=None, description="User that produced this build output."
    )
    pipeline_id: Union[UUID, str] = Field(
        default=None, description="Pipeline associated with the build output."
    )
    stack_id: Union[UUID, str] = Field(
        default=None, description="Stack used for the Pipeline Run"
    )


# ------- #
# REQUEST #
# ------- #


class BuildOutputRequestModel(
    BuildOutputBaseModel, WorkspaceScopedRequestModel
):
    """Request model for build outputs."""

    id: Optional[UUID] = None
    stack: Optional[UUID] = None
    pipeline: Optional[UUID] = None
