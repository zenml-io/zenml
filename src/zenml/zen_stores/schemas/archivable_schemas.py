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

from typing import TYPE_CHECKING, Optional, Union, cast
from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Field, SQLModel, col
from typing_extensions import Self

from zenml.exceptions import ExecutionArchivedError
from zenml.zen_stores.schemas.archive_detail import BundleDetail, Record

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.base_schemas import BaseSchema


class ArchivableSchema(SQLModel):
    """Retain identity in SQL while detail lives in an immutable bundle."""

    archive_bundle_id: Optional[UUID] = Field(nullable=True, default=None)

    @property
    def is_offloaded(self) -> bool:
        """Whether a bundle holds this entity's detail.

        Returns:
            True when the authority pointer is set.
        """
        return self.archive_bundle_id is not None

    def offloaded_detail(
        self,
        detail: Optional[BundleDetail],
        root_run_id: Optional[UUID] = None,
    ) -> Union[Self, Record]:
        """Select the authoritative payload without reading SQL or storage.

        Args:
            detail: Verified archived records, if the request loaded them.
            root_run_id: Canonical run to name in a restore command.

        Returns:
            This unarchived row or its matching immutable archived record.

        Raises:
            ExecutionArchivedError: Archived detail has not been loaded.
        """
        if not self.is_offloaded:
            return self
        row = cast("BaseSchema", self)
        if detail is None:
            raise ExecutionArchivedError.for_entity(row.id, root_run_id)
        return detail.record_for(row)

    @classmethod
    def not_offloaded(cls) -> ColumnElement[bool]:
        """Select entities whose detail remains in SQL.

        Returns:
            The SQL predicate for an unset authority pointer.
        """
        return col(cls.archive_bundle_id).is_(None)
