"""add settings table [84eee3df75e8].

Revision ID: 84eee3df75e8
Revises: 2d201872e23c
Create Date: 2024-04-22 21:56:48.119457

"""

from uuid import UUID

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "84eee3df75e8"
down_revision = "2d201872e23c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    from zenml.config.global_config import GlobalConfiguration

    op.create_table(
        "settings",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "logo_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("enable_analytics", sa.Boolean(), nullable=False),
        sa.Column("display_announcements", sa.Boolean(), nullable=False),
        sa.Column("display_updates", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Get metadata from current connection
    meta = sa.MetaData(bind=op.get_bind())

    # Pass in tuple with tables we want to reflect, otherwise whole database
    # will get reflected
    meta.reflect(only=("identity", "settings"))

    # Fetch the deployment id from the identity table
    deployment_id = (
        sa.select([meta.tables["identity"].c.id]).limit(1).execute().fetchone()
    )

    opt_in = GlobalConfiguration().analytics_opt_in

    # Prefill the settings table with a single row that contains the deployment
    # id extracted from the former identity table and some default settings
    op.bulk_insert(
        sa.Table(
            "settings",
            meta,
        ),
        [
            {
                "id": deployment_id,
                # Use the deployment ID as the default server name
                "name": str(UUID(deployment_id)),
                # Existing servers have already been activated
                "active": True,
                # Enable analytics if already enabled through the global config
                "enable_analytics": opt_in,
                # Enable announcements and updates if analytics is enabled
                "display_announcements": opt_in,
                "display_updates": opt_in,
            },
        ],
    )

    op.drop_table("identity")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.create_table(
        "identity",
        sa.Column("id", sa.CHAR(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Get metadata from current connection
    meta = sa.MetaData(bind=op.get_bind())

    # Pass in tuple with tables we want to reflect, otherwise whole database
    # will get reflected
    meta.reflect(only=("identity", "settings"))

    # Fetch the deployment id from the settings table
    deployment_id = (
        sa.select([meta.tables["settings"].c.id]).limit(1).execute().fetchone()
    )

    # Prefill the identity table with a single row that contains the deployment
    # id extracted from the settings table
    op.bulk_insert(
        sa.Table(
            "identity",
            meta,
        ),
        [
            {
                "id": deployment_id,
            },
        ],
    )

    op.drop_table("settings")
