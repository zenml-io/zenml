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
"""SQLModel implementation of idempotent transaction tables."""

from typing import Optional
from uuid import UUID

from sqlmodel import Field

from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema


class TransactionSchema(BaseSchema, table=True):
    """SQL Model for transactions."""

    __tablename__ = "transaction"

    completed: bool = Field(default=False)
    status_code: Optional[int] = Field(default=None, nullable=True)
    response: Optional[bytes] = Field(default=None, nullable=True)

    user_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
