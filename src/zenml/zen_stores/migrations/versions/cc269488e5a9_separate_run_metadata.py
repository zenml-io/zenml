"""separate run metadata [cc269488e5a9].

Revision ID: cc269488e5a9
Revises: 904464ea4041
Create Date: 2024-11-12 09:46:46.587478

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "cc269488e5a9"
down_revision = "904464ea4041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the 'run_metadata_resource_link' table."""
    # Create the `run_metadata_resource_link` table
    op.create_table(
        "run_metadata_resource_link",
        sa.Column("resource_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("resource_type", sa.String(length=255), nullable=False),
        sa.Column(
            "run_metadata_id",
            sa.Integer,
            sa.ForeignKey("run_metadata.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )

    # Migrate existing data from `run_metadata` to `run_metadata_resource`
    connection = op.get_bind()

    # Fetch data from the existing `run_metadata` table
    run_metadata_data = connection.execute(
        sa.text("""
            SELECT id, resource_id, resource_type
            FROM run_metadata
        """)
    ).fetchall()

    # Insert data into the new `run_metadata_resource` table
    for row in run_metadata_data:
        # Insert resource data with reference to `run_metadata`
        connection.execute(
            sa.text("""
                INSERT INTO run_metadata_resource_link (resource_id, resource_type, run_metadata_id)
                VALUES (:id, :resource_id, :resource_type, :run_metadata_id)
            """),
            {
                "resource_id": row.resource_id,
                "resource_type": row.resource_type,
                "run_metadata_id": row.id,
            },
        )

    # Drop the old `resource_id` and `resource_type` columns from `run_metadata`
    op.drop_column("run_metadata", "resource_id")
    op.drop_column("run_metadata", "resource_type")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
