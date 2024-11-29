"""Separate run metadata into resource link table with new UUIDs.

Revision ID: cc269488e5a9
Revises: ec6307720f92
Create Date: 2024-11-12 09:46:46.587478
"""

import uuid

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "cc269488e5a9"
down_revision = "ec6307720f92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the 'run_metadata_resource' table and migrates data."""
    op.create_table(
        "run_metadata_resource",
        sa.Column(
            "id",
            sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("resource_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("resource_type", sa.String(length=255), nullable=False),
        sa.Column(
            "run_metadata_id",
            sqlmodel.sql.sqltypes.GUID(),
            sa.ForeignKey("run_metadata.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )

    connection = op.get_bind()

    run_metadata_data = connection.execute(
        sa.text("""
            SELECT id, resource_id, resource_type
            FROM run_metadata
        """)
    ).fetchall()

    # Prepare data with new UUIDs for bulk insert
    resource_data = [
        {
            "id": str(uuid.uuid4()),  # Generate a new UUID for each row
            "resource_id": row.resource_id,
            "resource_type": row.resource_type,
            "run_metadata_id": row.id,
        }
        for row in run_metadata_data
    ]

    # Perform bulk insert into `run_metadata_resource`
    if resource_data:  # Only perform insert if there's data to migrate
        op.bulk_insert(
            sa.table(
                "run_metadata_resource",
                sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
                sa.Column(
                    "resource_id", sqlmodel.sql.sqltypes.GUID(), nullable=False
                ),
                sa.Column(
                    "resource_type", sa.String(length=255), nullable=False
                ),
                sa.Column(
                    "run_metadata_id",
                    sqlmodel.sql.sqltypes.GUID(),
                    nullable=False,
                ),  # Changed to BIGINT
            ),
            resource_data,
        )

    op.drop_column("run_metadata", "resource_id")
    op.drop_column("run_metadata", "resource_type")

    op.add_column(
        "run_metadata",
        sa.Column(
            "publisher_step_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
        ),
    )


def downgrade() -> None:
    """Reverts the 'run_metadata_resource' table and migrates data back."""
    # Recreate the `resource_id` and `resource_type` columns in `run_metadata`
    op.add_column(
        "run_metadata",
        sa.Column("resource_id", sqlmodel.sql.sqltypes.GUID(), nullable=True),
    )
    op.add_column(
        "run_metadata",
        sa.Column("resource_type", sa.String(length=255), nullable=True),
    )

    # Migrate data back from `run_metadata_resource` to `run_metadata`
    connection = op.get_bind()

    # Fetch data from `run_metadata_resource`
    run_metadata_resource_data = connection.execute(
        sa.text("""
            SELECT resource_id, resource_type, run_metadata_id
            FROM run_metadata_resource
        """)
    ).fetchall()

    # Update `run_metadata` with the data from `run_metadata_resource`
    for row in run_metadata_resource_data:
        connection.execute(
            sa.text("""
                UPDATE run_metadata
                SET resource_id = :resource_id, resource_type = :resource_type
                WHERE id = :run_metadata_id
            """),
            {
                "resource_id": row.resource_id,
                "resource_type": row.resource_type,
                "run_metadata_id": row.run_metadata_id,
            },
        )

    # Drop the `run_metadata_resource` table
    op.drop_table("run_metadata_resource")

    # Drop the cached column
    op.drop_column("run_metadata", "publisher_step_id")
