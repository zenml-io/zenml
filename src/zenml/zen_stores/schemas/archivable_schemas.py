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
"""Shared SQL authority marker for archived execution detail."""

from typing import TYPE_CHECKING, Optional, cast
from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Field, SQLModel, col

from zenml.exceptions import ExecutionArchivedError
from zenml.zen_stores.schemas.archive_detail import BundleDetail

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.base_schemas import BaseSchema


class ArchivableSchema(SQLModel):
    """Retain identity in SQL while detail lives in an immutable bundle."""

    archive_bundle_id: Optional[UUID] = Field(nullable=True, default=None)

    @property
    def is_archived(self) -> bool:
        """Whether a bundle holds this entity's detail.

        Returns:
            True when the authority pointer is set.
        """
        return self.archive_bundle_id is not None

    def archived_detail(
        self,
        detail: Optional[BundleDetail],
        run_id: Optional[UUID] = None,
    ) -> Optional[BundleDetail]:
        """Select where this entity's payload must be read from.

        Args:
            detail: Verified archived records, if the request loaded them.
            run_id: Run to name in a restore command.

        Returns:
            The loaded archive index for an archived entity, or None when the
            payload is still in this SQL row.

        Raises:
            ExecutionArchivedError: Archived detail has not been loaded.
        """
        if not self.is_archived:
            return None
        if detail is None:
            row = cast("BaseSchema", self)
            raise ExecutionArchivedError.for_entity(row.id, run_id)
        return detail

    @classmethod
    def not_archived(cls) -> ColumnElement[bool]:
        """Select entities whose detail remains in SQL.

        Returns:
            The SQL predicate for an unset authority pointer.
        """
        return col(cls.archive_bundle_id).is_(None)
