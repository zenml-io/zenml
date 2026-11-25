"""Add parent run and pipeline outputs [c2f8d07a91b4].

Revision ID: c2f8d07a91b4
Revises: f2c8e4a1903b
Create Date: 2026-04-27 15:20:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "c2f8d07a91b4"
down_revision = "f2c8e4a1903b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "parent_run_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "root_run_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "child_key",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_pipeline_run_parent_run_id_pipeline_run",
            "pipeline_run",
            ["parent_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_run_root_run_id_pipeline_run",
            "pipeline_run",
            ["root_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_pipeline_run_parent_run_id",
            ["parent_run_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_pipeline_run_root_run_id",
            ["root_run_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "unique_child_key_for_parent_run_id",
            ["parent_run_id", "child_key"],
        )

    op.create_table(
        "pipeline_run_output",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("output_index", sa.Integer(), nullable=False),
        sa.Column(
            "pipeline_run_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name="fk_pipeline_run_output_pipeline_run_id_pipeline_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifact_version.id"],
            name="fk_pipeline_run_output_artifact_id_artifact_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "name",
            name="unique_pipeline_run_output_name",
        ),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "output_index",
            name="unique_pipeline_run_output_index",
        ),
    )
    op.create_index(
        "ix_pipeline_run_output_artifact_id",
        "pipeline_run_output",
        ["artifact_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_index(
        "ix_pipeline_run_output_artifact_id",
        table_name="pipeline_run_output",
    )
    op.drop_table("pipeline_run_output")

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_child_key_for_parent_run_id",
            type_="unique",
        )
        batch_op.drop_index("ix_pipeline_run_root_run_id")
        batch_op.drop_index("ix_pipeline_run_parent_run_id")
        batch_op.drop_constraint(
            "fk_pipeline_run_root_run_id_pipeline_run",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_pipeline_run_parent_run_id_pipeline_run",
            type_="foreignkey",
        )

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("child_key")
        batch_op.drop_column("root_run_id")
        batch_op.drop_column("parent_run_id")
