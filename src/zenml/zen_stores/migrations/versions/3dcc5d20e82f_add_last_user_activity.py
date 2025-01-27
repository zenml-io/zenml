"""add last_user_activity [3dcc5d20e82f].

Revision ID: 3dcc5d20e82f
Revises: 909550c7c4da
Create Date: 2024-08-07 14:49:07.623500

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

from zenml.utils.time_utils import utc_now

# revision identifiers, used by Alembic.
revision = "3dcc5d20e82f"
down_revision = "026d4577b6a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    bind = op.get_bind()
    session = sqlmodel.Session(bind=bind)

    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("last_user_activity", sa.DateTime(), nullable=True)
        )

    session.execute(
        sa.text(
            """
            UPDATE server_settings
            SET last_user_activity = :last_user_activity
            """
        ),
        params=(dict(last_user_activity=utc_now())),
    )

    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "last_user_activity", existing_type=sa.DateTime(), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.drop_column("last_user_activity")
