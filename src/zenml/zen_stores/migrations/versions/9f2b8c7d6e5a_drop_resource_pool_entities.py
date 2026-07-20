"""Drop resource pool and request entities [9f2b8c7d6e5a].

Revision ID: 9f2b8c7d6e5a
Revises: 0.96.2
Create Date: 2026-06-20 00:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "9f2b8c7d6e5a"
down_revision = "0.96.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.drop_table("resource_pool_queue")
    op.drop_table("resource_pool_allocation")
    op.drop_table("resource_pool_subject_policy_resource")
    op.drop_table("resource_pool_subject_policy")
    op.drop_table("resource_pool_resource")
    op.drop_table("resource_pool")
    op.drop_table("resource_request_resource")
    op.drop_table("resource_request")
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "resource_request_id",
                sqlmodel.sql.sqltypes.GUID(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # Downgrades are not generally supported in ZenML.
