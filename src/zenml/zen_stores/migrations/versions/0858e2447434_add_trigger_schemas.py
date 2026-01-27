"""Add trigger schemas [0858e2447434].

Revision ID: 0858e2447434
Revises: 97109a4a8d26
Create Date: 2026-01-27 16:06:46.129946

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "0858e2447434"
down_revision = "97109a4a8d26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        "trigger",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("trigger_type", sa.VARCHAR(length=20), nullable=False),
        sa.Column("category", sa.VARCHAR(length=50), nullable=False),
        sa.Column(
            "data",
            sa.String(length=16777215).with_variant(
                mysql.MEDIUMTEXT(), "mysql"
            ),
            nullable=False,
        ),
        sa.Column("project_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True),
        sa.Column("next_occurrence", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_trigger_project_id_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_trigger_user_id_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name", "project_id", name="unique_trigger_name_in_project"
        ),
    )
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.create_index(
            "ix_trigger_category", ["category"], unique=False
        )
        batch_op.create_index(
            "ix_trigger_category_next_occurrence",
            ["category", "next_occurrence"],
            unique=False,
        )
        batch_op.create_index(
            "ix_trigger_trigger_type", ["trigger_type"], unique=False
        )

    op.create_table(
        "snapshot_trigger",
        sa.Column("trigger_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("snapshot_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["pipeline_snapshot.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["trigger_id"], ["trigger.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("trigger_id", "snapshot_id"),
        sa.UniqueConstraint(
            "trigger_id", "snapshot_id", name="unique_trigger_snapshot_link"
        ),
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_table("snapshot_trigger")
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_index("ix_trigger_trigger_type")
        batch_op.drop_index("ix_trigger_category_next_occurrence")
        batch_op.drop_index("ix_trigger_category")

    op.drop_table("trigger")
