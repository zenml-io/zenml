"""Artifact Version Table [a91762e6be36].

Revision ID: a91762e6be36
Revises: 0.50.0
Create Date: 2023-11-25 11:01:09.217299

"""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "a91762e6be36"
down_revision = "0.50.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Rename old artifact table to artifact_version
    op.rename_table("artifact", "artifact_version")

    # Create new artifact table
    op.create_table(
        "artifact",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=255), nullable=False),
        sa.Column("has_custom_name", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add foreign key column to artifact_version, for now as nullable
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "artifact_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Find all unique artifact names and create a new artifact entry for each
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(only=("artifact", "artifact_version"), bind=op.get_bind())
    artifacts = sa.Table("artifact", meta)
    artifact_versions = sa.Table("artifact_version", meta)
    artifact_names = conn.execute(
        sa.select(
            artifact_versions.c.name, artifact_versions.c.has_custom_name
        ).distinct()
    ).all()
    unique_artifact_names = {
        name: has_custom_name for name, has_custom_name in artifact_names
    }
    for name, has_custom_name in unique_artifact_names.items():
        conn.execute(
            artifacts.insert().values(
                id=uuid4().hex,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
                name=name,
                has_custom_name=has_custom_name,
            )
        )

    # Set artifact_id column in artifact_version
    conn.execute(
        artifact_versions.update().values(
            artifact_id=sa.select(artifacts.c.id)
            .where(artifacts.c.name == artifact_versions.c.name)
            .scalar_subquery()
        )
    )

    # Make foreign key column non-nullable and create constraint
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.alter_column(
            "artifact_id", nullable=False, existing_type=sa.CHAR(length=32)
        )
        batch_op.create_foreign_key(
            "fk_artifact_version_artifact_id_artifact",
            "artifact",
            ["artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Drop old columns from artifact_version
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.drop_column("name")
        batch_op.drop_column("has_custom_name")

    # Rename constraints `fk_artifact_...` to `fk_artifact_version_...`
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_artifact_artifact_store_id_stack_component", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_artifact_user_id_user", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_artifact_workspace_id_workspace", type_="foreignkey"
        )
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_artifact_version_artifact_store_id_stack_component",
            "stack_component",
            ["artifact_store_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_artifact_version_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_artifact_version_workspace_id_workspace",
            "workspace",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Rename constraints of other tables
    with op.batch_alter_table(
        "artifact_visualization", schema=None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_artifact_visualization_artifact_id_artifact",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "artifact_id",
            new_column_name="artifact_version_id",
            existing_type=sa.CHAR(length=32),
        )
    with op.batch_alter_table(
        "artifact_visualization", schema=None
    ) as batch_op:
        batch_op.create_foreign_key(
            "fk_artifact_visualization_artifact_version_id_artifact_version",
            "artifact_version",
            ["artifact_version_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table(
        "model_versions_artifacts", schema=None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_model_versions_artifacts_artifact_id_artifact",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "artifact_id",
            new_column_name="artifact_version_id",
            existing_type=sa.CHAR(length=32),
        )
    with op.batch_alter_table(
        "model_versions_artifacts", schema=None
    ) as batch_op:
        batch_op.create_foreign_key(
            "fk_model_versions_artifacts_artifact_version_id_artifact_version",
            "artifact_version",
            ["artifact_version_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("run_metadata", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_run_metadata_artifact_id_artifact", type_="foreignkey"
        )
        batch_op.alter_column(
            "artifact_id",
            new_column_name="artifact_version_id",
            existing_type=sa.CHAR(length=32),
        )
    with op.batch_alter_table("run_metadata", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_run_metadata_artifact_version_id_artifact_version",
            "artifact_version",
            ["artifact_version_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_step_run_input_artifact_artifact_id_artifact",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_step_run_input_artifact_artifact_id_artifact_version",
            "artifact_version",
            ["artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table(
        "step_run_output_artifact", schema=None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_step_run_output_artifact_artifact_id_artifact",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_step_run_output_artifact_artifact_id_artifact_version",
            "artifact_version",
            ["artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not supported for this migration.
    """
    raise NotImplementedError("Downgrade is not supported for this migration.")
