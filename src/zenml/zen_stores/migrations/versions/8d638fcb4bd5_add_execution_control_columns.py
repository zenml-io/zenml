"""Add execution control columns [8d638fcb4bd5].

Revision ID: 8d638fcb4bd5
Revises: c7d4e8a2b5f1
Create Date: 2026-09-24 00:20:46.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "8d638fcb4bd5"
down_revision = "c7d4e8a2b5f1"
branch_labels = None
depends_on = None

# JSON values without a practical size bound use the same type as the
# configuration columns they are derived from.
JSON_TEXT_TYPE = sa.String(length=16777215).with_variant(
    mysql.MEDIUMTEXT, "mysql"
)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # All columns are nullable and appended, so MySQL can add them without
    # rebuilding these large tables. Existing rows keep NULL values and are
    # read through the previous JSON-parsing code path.
    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "execution_mode",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("enable_heartbeat", sa.Boolean(), nullable=True)
        )

    with op.batch_alter_table("step_configuration", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("upstream_steps", JSON_TEXT_TYPE, nullable=True)
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "step_type",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("substitutions", JSON_TEXT_TYPE, nullable=True)
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("substitutions")
        batch_op.drop_column("step_type")

    with op.batch_alter_table("step_configuration", schema=None) as batch_op:
        batch_op.drop_column("upstream_steps")

    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.drop_column("enable_heartbeat")
        batch_op.drop_column("execution_mode")
