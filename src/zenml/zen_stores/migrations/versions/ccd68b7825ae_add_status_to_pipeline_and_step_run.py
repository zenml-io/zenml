"""Add status to pipeline and step run [ccd68b7825ae].

Revision ID: ccd68b7825ae
Revises: c1b18cec3a48
Create Date: 2022-10-24 16:49:37.007641

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "ccd68b7825ae"
down_revision = "c1b18cec3a48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipelinerunschema", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "status", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            ),
        )
    op.execute("UPDATE pipelinerunschema SET status = 'running'")
    with op.batch_alter_table("pipelinerunschema", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
        )

    with op.batch_alter_table("steprunschema", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "status", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            ),
        )
    op.execute("UPDATE steprunschema SET status = 'running'")
    with op.batch_alter_table("steprunschema", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("steprunschema", schema=None) as batch_op:
        batch_op.drop_column("status")

    with op.batch_alter_table("pipelinerunschema", schema=None) as batch_op:
        batch_op.drop_column("status")
