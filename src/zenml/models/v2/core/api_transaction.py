#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Models representing API transactions."""

from typing import (
    TYPE_CHECKING,
    Optional,
    TypeVar,
)
from uuid import UUID

from pydantic import Field, SecretStr

from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)
from zenml.utils.secret_utils import PlainSerializedSecretStr

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

# ------------------ Request Model ------------------


class ApiTransactionRequest(UserScopedRequest):
    """Request model for API transactions."""

    transaction_id: UUID = Field(
        title="The ID of the transaction.",
    )
    method: str = Field(
        title="The HTTP method of the transaction.",
    )
    url: str = Field(
        title="The URL of the transaction.",
    )


# ------------------ Update Model ------------------


class ApiTransactionUpdate(BaseUpdate):
    """Update model for stack components."""

    result: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="The response payload.",
    )
    cache_time: int = Field(
        title="The time in seconds that the transaction is kept around after "
        "completion."
    )

    def get_result(self) -> Optional[str]:
        """Get the result of the API transaction.

        Returns:
            the result of the API transaction.
        """
        result = self.result
        if result is None:
            return None
        return result.get_secret_value()

    def set_result(self, result: str) -> None:
        """Set the result of the API transaction.

        Args:
            result: the result of the API transaction.
        """
        self.result = SecretStr(result)


# ------------------ Response Model ------------------


class ApiTransactionResponseBody(UserScopedResponseBody):
    """Response body for API transactions."""

    method: str = Field(
        title="The HTTP method of the transaction.",
    )
    url: str = Field(
        title="The URL of the transaction.",
    )
    completed: bool = Field(
        title="Whether the transaction is completed.",
    )
    result: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="The response payload.",
    )


class ApiTransactionResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for API transactions."""


class ApiTransactionResponseResources(UserScopedResponseResources):
    """Response resources for API transactions."""


class ApiTransactionResponse(
    UserScopedResponse[
        ApiTransactionResponseBody,
        ApiTransactionResponseMetadata,
        ApiTransactionResponseResources,
    ]
):
    """Response model for API transactions."""

    def get_hydrated_version(self) -> "ApiTransactionResponse":
        """Get the hydrated version of this API transaction.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        return self

    # Body and metadata properties

    @property
    def method(self) -> str:
        """The `method` property.

        Returns:
            the value of the property.
        """
        return self.get_body().method

    @property
    def url(self) -> str:
        """The `url` property.

        Returns:
            the value of the property.
        """
        return self.get_body().url

    @property
    def completed(self) -> bool:
        """The `completed` property.

        Returns:
            the value of the property.
        """
        return self.get_body().completed

    @property
    def result(self) -> Optional[PlainSerializedSecretStr]:
        """The `result` property.

        Returns:
            the value of the property.
        """
        return self.get_body().result

    def get_result(self) -> Optional[str]:
        """Get the result of the API transaction.

        Returns:
            the result of the API transaction.
        """
        result = self.result
        if result is None:
            return None
        return result.get_secret_value()

    def set_result(self, result: str) -> None:
        """Set the result of the API transaction.

        Args:
            result: the result of the API transaction.
        """
        self.get_body().result = SecretStr(result)
