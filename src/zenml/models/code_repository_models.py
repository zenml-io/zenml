#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
)

# --------------- #
# CODE REFERENCES #
# --------------- #


class CodeReferenceBaseModel(BaseModel):
    """Base model for code references."""

    commit: str = Field(description="The commit of the code reference.")
    subdirectory: str = Field(
        description="The subdirectory of the code reference."
    )


class CodeReferenceRequestModel(CodeReferenceBaseModel, BaseRequestModel):
    """Code reference request model."""

    code_repository: UUID = Field(
        description="The repository of the code reference."
    )


class CodeReferenceResponseModel(CodeReferenceBaseModel, BaseResponseModel):
    """Code reference response model."""

    code_repository: CodeRepositoryResponseModel = Field(
        description="The repository of the code reference."
    )
