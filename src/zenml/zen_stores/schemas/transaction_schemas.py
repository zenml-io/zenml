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
"""SQLModel implementation of idempotency transaction tables."""

from typing import List
from uuid import UUID

from sqlalchemy import VARCHAR, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema


class TransactionSchema(BaseSchema, table=True):
    """SQL Model for transactions."""

    __tablename__ = "transaction"

    completed: bool = Field(default=False)
    user_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    resources: List["TransactionResourceSchema"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"cascade": "delete"},
    )


class TransactionResourceSchema(SQLModel, table=True):
    """SQL Model for resources that are part of a transaction."""

    __tablename__ = "transaction_resource"
    __table_args__ = (
        build_index(
            table_name=__tablename__,
            column_names=[
                "resource_id",
                "resource_type",
                "transaction_id",
            ],
        ),
    )

    transaction_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=TransactionSchema.__tablename__,
        source_column="transaction_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    transaction: "TransactionSchema" = Relationship(back_populates="resources")
    resource_id: UUID
    resource_type: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
