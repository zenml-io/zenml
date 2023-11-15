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

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import Field

from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)

if TYPE_CHECKING:
    from zenml.models.v2.core.code_repository import CodeRepositoryResponse


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


class CodeReferenceResponse(
    BaseResponse[CodeReferenceResponseBody, CodeReferenceResponseMetadata]
):
    """Response model for code references."""

    def get_hydrated_version(self) -> "CodeReferenceResponse":
        """Get the hydrated version of this code reference.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_code_reference(self.id)

    # Body and metadata properties
    @property
    def commit(self) -> str:
        """The `commit` property.

        Returns:
            the value of the property.
        """
        return self.get_body().commit

    @property
    def subdirectory(self) -> str:
        """The `subdirectory` property.

        Returns:
            the value of the property.
        """
        return self.get_body().subdirectory

    @property
    def code_repository(self) -> "CodeRepositoryResponse":
        """The `code_repository` property.

        Returns:
            the value of the property.
        """
        return self.get_body().code_repository


# ------------------ Filter Model ------------------

# There is no filter model for code references.
