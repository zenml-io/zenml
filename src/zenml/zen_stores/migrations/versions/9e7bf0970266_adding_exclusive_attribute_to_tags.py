"""adding exclusive attribute to tags [9e7bf0970266].

Revision ID: 9e7bf0970266
Revises: 2e695a26fe7a
Create Date: 2025-03-03 15:17:49.341208

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9e7bf0970266"
down_revision = "2e695a26fe7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Use batch_alter_table for safer schema modifications
    with op.batch_alter_table("tag") as batch_op:
        # First add the column as nullable
        batch_op.add_column(
            sa.Column(
                "exclusive",
                sa.Boolean(),
                nullable=True,
            ),
        )

    # Update existing rows with default value
    op.execute("UPDATE tag SET exclusive = FALSE WHERE exclusive IS NULL")

    # Then alter the column to be non-nullable with a default
    with op.batch_alter_table("tag") as batch_op:
        batch_op.alter_column(
            "exclusive",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_column("tag", "exclusive")
