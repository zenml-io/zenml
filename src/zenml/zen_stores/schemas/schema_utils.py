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
"""Utility functions for SQLModel schemas."""

from typing import Any

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field


def foreign_key_constraint_name(
    source: str, target: str, source_column: str
) -> str:
    """Defines the name of a foreign key constraint.

    For simplicity, we use the naming convention used by alembic here:
    https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints.

    Args:
        source: Source table name.
        target: Target table name.
        source_column: Source column name.

    Returns:
        Name of the foreign key constraint.
    """
    return f"fk_{source}_{source_column}_{target}"


def build_foreign_key_field(
    source: str,
    target: str,
    source_column: str,
    target_column: str,
    ondelete: str,
    nullable: bool,
    **sa_column_kwargs: Any,
) -> Any:
    """Build a SQLModel foreign key field.

    Args:
        source: Source table name.
        target: Target table name.
        source_column: Source column name.
        target_column: Target column name.
        ondelete: On delete behavior.
        nullable: Whether the field is nullable.
        **sa_column_kwargs: Keyword arguments for the SQLAlchemy column.

    Returns:
        SQLModel foreign key field.

    Raises:
        ValueError: If the ondelete and nullable arguments are not compatible.
    """
    if not nullable and ondelete == "SET NULL":
        raise ValueError(
            "Cannot set ondelete to SET NULL if the field is not nullable."
        )
    constraint_name = foreign_key_constraint_name(
        source=source,
        target=target,
        source_column=source_column,
    )
    return Field(
        sa_column=Column(
            ForeignKey(
                f"{target}.{target_column}",
                name=constraint_name,
                ondelete=ondelete,
            ),
            nullable=nullable,
            **sa_column_kwargs,
        ),
    )
