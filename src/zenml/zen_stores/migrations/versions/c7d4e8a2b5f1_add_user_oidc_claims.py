"""Add user OIDC claims [c7d4e8a2b5f1].

Revision ID: c7d4e8a2b5f1
Revises: 9f2b8c7d6e5a
Create Date: 2026-09-22 00:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "c7d4e8a2b5f1"
down_revision = "9f2b8c7d6e5a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the OIDC claims column to users."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "oidc_claims",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Remove the OIDC claims column from users."""
    # Downgrades are not generally supported in ZenML.
