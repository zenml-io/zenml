"""move artifact save type [1cb6477f72d6].

Revision ID: 1cb6477f72d6
Revises: 0.68.1
Create Date: 2024-10-10 15:44:09.465210

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1cb6477f72d6"
down_revision = "0.68.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Step 1: Add nullable save_type column to artifact_version
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.add_column(sa.Column("save_type", sa.TEXT(), nullable=True))

    # Step 2: Move data from step_run_output_artifact.type to artifact_version.save_type
    op.execute("""
        UPDATE artifact_version
        SET save_type = (
            SELECT step_run_output_artifact.type
            FROM step_run_output_artifact
            WHERE step_run_output_artifact.artifact_id = artifact_version.id
        )
    """)
    op.execute("""
        UPDATE artifact_version
        SET save_type = 'step_output'
        WHERE artifact_version.save_type = 'default'
    """)
    op.execute("""
        UPDATE artifact_version
        SET save_type = 'external'
        WHERE save_type is NULL
    """)

    # # Step 3: Set save_type to non-nullable
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.alter_column(
            "save_type",
            existing_type=sa.TEXT(),
            nullable=False,
        )

    # Step 4: Remove type column from step_run_output_artifact
    with op.batch_alter_table(
        "step_run_output_artifact", schema=None
    ) as batch_op:
        batch_op.drop_column("type")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # Add type column back to step_run_output_artifact
    with op.batch_alter_table(
        "step_run_output_artifact", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column("type", sa.TEXT(), nullable=True),
        )

    # Move data back from artifact_version.save_type to step_run_output_artifact.type
    op.execute("""
        UPDATE step_run_output_artifact
        SET type = (
            SELECT artifact_version.save_type
            FROM artifact_version
            WHERE step_run_output_artifact.artifact_id = artifact_version.id
        )
    """)
    op.execute("""
        UPDATE step_run_output_artifact
        SET type = 'default'
        WHERE step_run_output_artifact.type = 'step_output'
    """)

    # Set type to non-nullable
    with op.batch_alter_table(
        "step_run_output_artifact", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=sa.TEXT(),
            nullable=False,
        )

    # Remove save_type column from artifact_version
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.drop_column("save_type")
