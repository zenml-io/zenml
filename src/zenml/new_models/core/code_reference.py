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
"""Models representing code references."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import Field

from zenml.new_models.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)

if TYPE_CHECKING:
    from zenml.new_models.core.code_repository import (
        CodeRepositoryResponse,
    )


# ------------------ Request Model ------------------


class CodeReferenceRequest(BaseRequest):
    """Request model for code references."""

    commit: str = Field(description="The commit of the code reference.")
    subdirectory: str = Field(
        description="The subdirectory of the code reference."
    )
    code_repository: UUID = Field(
        description="The repository of the code reference."
    )


# ------------------ Update Model ------------------

# There is no update model for code references.


# ------------------ Response Model ------------------


class CodeReferenceResponseBody(BaseResponseBody):
    """Response body for code references."""

    commit: str = Field(description="The commit of the code reference.")
    subdirectory: str = Field(
        description="The subdirectory of the code reference."
    )
    code_repository: "CodeRepositoryResponse" = Field(
        description="The repository of the code reference."
    )


class CodeReferenceResponseMetadata(BaseResponseMetadata):
    """Response metadata for code references."""


class CodeReferenceResponse(BaseResponse):
    """Response model for code references."""

    # Body and metadata pair
    body: "CodeReferenceResponseBody"
    metadata: Optional["CodeReferenceResponseMetadata"]

    def get_hydrated_version(self) -> "CodeReferenceResponse":
        """Get the hydrated version of this code reference."""
        from zenml.client import Client

        return Client().get_code_reference(self.id)

    # Body and metadata properties
    @property
    def commit(self):
        """The `commit` property."""
        return self.body.commit

    @property
    def subdirectory(self):
        """The `subdirectory` property."""
        return self.body.subdirectory

    @property
    def code_repository(self):
        """The `code_repository` property."""
        return self.body.code_repository


# ------------------ Filter Model ------------------

# There is no filter model for code references.
