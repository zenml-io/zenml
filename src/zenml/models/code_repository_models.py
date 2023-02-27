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
"""Models representing code repositories."""

from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.source import Source
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel

# ---- #
# BASE #
# ---- #


class CodeRepositoryBaseModel(BaseModel):
    """Base model for code repositories."""

    name: str = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    config: Dict[str, Any]
    source: Source


# -------- #
# RESPONSE #
# -------- #


class CodeRepositoryResponseModel(
    CodeRepositoryBaseModel, WorkspaceScopedResponseModel
):
    """Code repository response model."""


# ------ #
# FILTER #
# ------ #


class CodeRepositoryFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all code repositories."""

    name: Optional[str] = Field(
        description="Name of the code repository.",
    )
    workspace_id: Union[UUID, str, None] = Field(
        description="Workspace of the code repository."
    )
    user_id: Union[UUID, str, None] = Field(
        description="User that created the code repository."
    )


# ------- #
# REQUEST #
# ------- #


class CodeRepositoryRequestModel(
    CodeRepositoryBaseModel, WorkspaceScopedRequestModel
):
    """Code repository request model."""


# ------ #
# UPDATE #
# ------ #


@update_model
class CodeRepositoryUpdateModel(CodeRepositoryRequestModel):
    """Code repository update model."""
