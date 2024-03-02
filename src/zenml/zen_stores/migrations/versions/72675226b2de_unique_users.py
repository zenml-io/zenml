"""unique users [72675226b2de].

Revision ID: 72675226b2de
Revises: 0.55.4
Create Date: 2024-02-29 14:58:25.584731

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "72675226b2de"
down_revision = "0.55.4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_user_name_is_service_account", ["name", "is_service_account"]
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_user_name_is_service_account", type_="unique"
        )
