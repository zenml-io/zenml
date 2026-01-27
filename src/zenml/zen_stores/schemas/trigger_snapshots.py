"""SQL Model Implementations for Triggers."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import PipelineSnapshotSchema, TriggerSchema


class TriggerSnapshotSchema(SQLModel, table=True):
    """Association table linking triggers to pipeline snapshots.

    - Enforces uniqueness per (trigger_id, snapshot_id)
    - Cascades deletes from either parent row (DB-level ON DELETE CASCADE)
    """

    __tablename__ = "trigger_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "trigger_id",
            "snapshot_id",
            name="unique_trigger_snapshot_link",
        ),
    )

    trigger_id: int = Field(
        sa_column=Column(
            ForeignKey("trigger.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
    )
    snapshot_id: int = Field(
        sa_column=Column(
            ForeignKey("pipeline_snapshot.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
    )

    created_at: datetime = Field(default_factory=utc_now)

    trigger: "TriggerSchema" = Relationship(back_populates="snapshot_links")
    snapshot: "PipelineSnapshotSchema" = Relationship(
        back_populates="trigger_links"
    )
