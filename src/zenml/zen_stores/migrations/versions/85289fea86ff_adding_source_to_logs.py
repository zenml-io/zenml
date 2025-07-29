"""Add log source [85289fea86ff].

Revision ID: 85289fea86ff
Revises: 5bb25e95849c
Create Date: 2025-06-30 18:18:24.539265

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "85289fea86ff"
down_revision = "5bb25e95849c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Add the source column as nullable first
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("source", sa.VARCHAR(255), nullable=True)
        )

    # Populate the source field based on existing data
    connection = op.get_bind()

    # Set source to "step" where step_run_id is present
    connection.execute(
        sa.text("""
            UPDATE logs 
            SET source = 'step' 
            WHERE step_run_id IS NOT NULL
        """)
    )

    # Set source to "client" for all other cases (where step_run_id is null)
    connection.execute(
        sa.text("""
            UPDATE logs 
            SET source = 'client' 
            WHERE step_run_id IS NULL
        """)
    )

    # Make the source column not nullable
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.VARCHAR(255),
            nullable=False,
        )
        # Add unique constraint: source is unique for each combination of pipeline_run_id and step_run_id
        batch_op.create_unique_constraint(
            "unique_source_per_run_and_step",
            ["source", "pipeline_run_id", "step_run_id"],
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_source_per_run_and_step", type_="unique"
        )
        batch_op.drop_column("source")
