#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Reusable helpers for database migrations."""

from typing import List, Optional

from alembic import op
from sqlalchemy import inspect


def index_exists(
    table_name: str, index_name: str, schema: Optional[str] = None
) -> bool:
    """Check whether an index exists on the current database connection."""
    connection = op.get_bind()
    inspector = inspect(connection)
    return any(
        index["name"] == index_name
        for index in inspector.get_indexes(table_name, schema=schema)
    )


def create_index_if_missing(
    table_name: str,
    index_name: str,
    columns: List[str],
    unique: bool = False,
    schema: Optional[str] = None,
) -> None:
    """Create an index only if it does not already exist."""
    if index_exists(table_name, index_name, schema=schema):
        return

    with op.batch_alter_table(table_name, schema=schema) as batch_op:
        batch_op.create_index(index_name, columns, unique=unique)


def drop_index_if_exists(
    table_name: str, index_name: str, schema: Optional[str] = None
) -> None:
    """Drop an index only if it exists."""
    if not index_exists(table_name, index_name, schema=schema):
        return

    with op.batch_alter_table(table_name, schema=schema) as batch_op:
        batch_op.drop_index(index_name)
