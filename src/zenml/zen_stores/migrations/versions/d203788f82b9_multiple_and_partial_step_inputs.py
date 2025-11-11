"""Multiple and partial step inputs [d203788f82b9].

Revision ID: d203788f82b9
Revises: 4dd9d3afd2c0
Create Date: 2025-11-11 11:57:39.370022

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d203788f82b9"
down_revision = "4dd9d3afd2c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("item_count", sa.Integer(), nullable=True)
        )

    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column("input_index", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("chunk_index", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("chunk_size", sa.Integer(), nullable=True)
        )

    op.execute(sa.text("UPDATE step_run_input_artifact SET input_index=0"))
    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "input_index",
            nullable=False,
            existing_type=sa.Integer(),
        )

    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "step_run_input_artifact", schema=None, recreate="always"
        ) as batch_op:
            batch_op.create_primary_key(
                constraint_name="PRIMARY",
                columns=["name", "step_id", "artifact_id", "input_index"],
            )
    else:
        with op.batch_alter_table(
            "step_run_input_artifact", schema=None
        ) as batch_op:
            batch_op.drop_constraint(
                constraint_name="PRIMARY",
                type_="primary",
            )
            batch_op.create_primary_key(
                constraint_name="PRIMARY",
                columns=["name", "step_id", "artifact_id", "input_index"],
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade not possible.
    """
    raise NotImplementedError("Downgrade not possible")
