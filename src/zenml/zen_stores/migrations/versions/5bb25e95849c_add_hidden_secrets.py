"""add hidden secrets [5bb25e95849c].

Revision ID: 5bb25e95849c
Revises: 0.83.1
Create Date: 2025-06-23 20:49:44.184630

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5bb25e95849c"
down_revision = "0.83.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Step 1: Add hidden column as nullable
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hidden", sa.Boolean(), nullable=True))

    # Step 2: Update existing records based on service connector references
    # If a secret is referenced by a service_connector.secret_id, make it hidden=True
    # Otherwise, set it to hidden=False
    connection = op.get_bind()

    # Update secrets that are referenced by service connectors to be hidden
    connection.execute(
        sa.text("""
            UPDATE secret 
            SET hidden = TRUE 
            WHERE id IN (
                SELECT DISTINCT secret_id 
                FROM service_connector 
                WHERE secret_id IS NOT NULL
            );
        """)
    )

    # Update all other secrets to be not hidden
    connection.execute(
        sa.text("""
            UPDATE secret 
            SET hidden = FALSE 
            WHERE hidden IS NULL;
        """)
    )

    # Step 3: Make hidden column non-nullable
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "hidden", existing_type=sa.Boolean(), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.drop_column("hidden")
