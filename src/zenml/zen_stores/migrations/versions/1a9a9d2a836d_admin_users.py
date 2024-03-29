"""admin users [1a9a9d2a836d].

Revision ID: 1a9a9d2a836d
Revises: 0.55.5
Create Date: 2024-03-04 15:48:16.580871

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "1a9a9d2a836d"
down_revision = "0.55.5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = sqlmodel.Session(bind=bind)

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            )
        )

    # during migration we treat all users as admin for backward compatibility
    # this should be adjusted by server admins after upgrade
    session.execute(
        sa.text(
            """
            UPDATE user
            SET is_admin = true
            WHERE NOT is_service_account AND external_user_id IS NULL
            """
        )
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("is_admin")

    # ### end Alembic commands ###
