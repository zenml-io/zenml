#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""SQLModel implementation of idempotent API transaction tables."""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models import (
    ApiTransactionRequest,
    ApiTransactionResponse,
    ApiTransactionResponseBody,
    ApiTransactionUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema


class ApiTransactionSchema(BaseSchema, table=True):
    """SQL Model for API transactions."""

    __tablename__ = "api_transaction"
    __table_args__ = (
        build_index(
            table_name=__tablename__,
            column_names=[
                "completed",
                "expired",
            ],
        ),
    )
    method: str
    url: str = Field(sa_column=Column(TEXT, nullable=False))
    completed: bool = Field(default=False)
    result: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        ),
    )
    expired: Optional[datetime] = Field(default=None, nullable=True)

    user_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    @classmethod
    def from_request(
        cls, request: ApiTransactionRequest
    ) -> "ApiTransactionSchema":
        """Create a new API transaction from a request.

        Args:
            request: The API transaction request.

        Returns:
            The API transaction schema.
        """
        assert request.user is not None, "User must be set."
        return cls(
            id=request.transaction_id,
            user_id=request.user,
            method=request.method,
            url=request.url,
            completed=False,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ApiTransactionResponse:
        """Convert the SQL model to a ZenML model.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            **kwargs: Additional keyword arguments.

        Returns:
            The API transaction response.
        """
        response = ApiTransactionResponse(
            id=self.id,
            body=ApiTransactionResponseBody(
                method=self.method,
                url=self.url,
                created=self.created,
                updated=self.updated,
                user_id=self.user_id,
                completed=self.completed,
            ),
        )
        if self.result is not None:
            response.set_result(self.result)
        return response

    def update(self, update: ApiTransactionUpdate) -> "ApiTransactionSchema":
        """Update the API transaction.

        Args:
            update: The API transaction update.

        Returns:
            The API transaction schema.
        """
        if update.result is not None:
            self.result = update.get_result()
        self.updated = utc_now()
        self.expired = self.updated + timedelta(seconds=update.cache_time)
        return self
