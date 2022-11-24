"""Optimization [d5d6192c6b83].

Revision ID: d5d6192c6b83
Revises: 0.22.0
Create Date: 2022-11-24 11:12:45.413747

"""
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5d6192c6b83'
down_revision = '0.22.0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Make description on Projects optional
    with op.batch_alter_table('workspace', schema=None) as batch_op:
        batch_op.alter_column(
            'description',
            existing_type=sa.VARCHAR(),
            nullable=True
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # Descriptions were not nullable on projects before this
    # get metadata from current connection
    meta = sa.MetaData(bind=op.get_bind())

    # pass in tuple with tables we want to reflect, otherwise whole database
    #  will get reflected
    meta.reflect(
        only=(
            "workspace",
        )
    )
    workspace = sa.Table(
        "workspace",
        meta,
    )
    # Set all project descriptions to an empty string

    # Make description column non-nullable
    with op.batch_alter_table('workspace', schema=None) as batch_op:
        batch_op.execute(
            workspace.update()
            .where(workspace.c.description is None)
            .values(description="blahblah")
        )
        batch_op.alter_column(
            'description',
            existing_type=sa.VARCHAR(),
            nullable=False
        )
