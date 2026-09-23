# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Shared archive-state filters and response fields for execution entities."""

from typing import TYPE_CHECKING, ClassVar, List, Optional, Type, TypeVar
from uuid import UUID

from pydantic import Field

from zenml.models.v2.base.base import BaseResponseBody, BaseZenModel
from zenml.models.v2.base.filter import AnyQuery, BaseFilter

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


class ArchivableFilter(BaseFilter):
    """Filter execution entities by whether their detail is archived."""

    is_archived: Optional[bool] = Field(
        default=None, description="Whether execution detail is archived."
    )
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "is_archived",
    ]

    def apply_filter(
        self, query: AnyQuery, table: Type["AnySchema"]
    ) -> AnyQuery:
        """Apply the archive-state predicate alongside the ordinary filters.

        Args:
            query: Query to filter.
            table: Execution schema containing an archive marker.

        Returns:
            The filtered query.
        """
        query = super().apply_filter(query=query, table=table)
        if self.is_archived is not None:
            marker = getattr(table, "archive_bundle_id")
            query = query.where(
                marker.is_not(None) if self.is_archived else marker.is_(None)
            )
        return query


class ExecutionArchiveDescriptor(BaseZenModel):
    """SQL-backed location of archived execution detail."""

    bundle_id: UUID = Field(title="The bundle that holds the archived detail.")
    restore_run_id: Optional[UUID] = Field(
        default=None,
        title="The run to restore before accessing cold detail.",
    )


class ArchivableResponseBody(BaseResponseBody):
    """Response body fields shared by entities whose detail can be archived."""

    archive_bundle_id: Optional[UUID] = Field(
        default=None,
        title="The archive bundle that holds archived detail, if any.",
    )
    archive: Optional[ExecutionArchiveDescriptor] = Field(
        default=None,
        title="SQL-backed information for discovering archived detail.",
    )
