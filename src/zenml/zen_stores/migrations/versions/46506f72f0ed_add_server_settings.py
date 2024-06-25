"""Add server settings [46506f72f0ed].

Revision ID: 46506f72f0ed
Revises: cc9894cb58aa
Create Date: 2024-04-17 14:17:08.142652

"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "46506f72f0ed"
down_revision = "cc9894cb58aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    from zenml.config.global_config import GlobalConfiguration

    op.create_table(
        "server_settings",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column(
            "server_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "logo_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("enable_analytics", sa.Boolean(), nullable=False),
        sa.Column("display_announcements", sa.Boolean(), nullable=False),
        sa.Column("display_updates", sa.Boolean(), nullable=False),
        sa.Column("onboarding_state", sa.TEXT(), nullable=True),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Get metadata from current connection
    meta = sa.MetaData()

    # Pass in tuple with tables we want to reflect, otherwise whole database
    # will get reflected
    meta.reflect(only=("identity", "server_settings"), bind=op.get_bind())

    # Fetch the deployment id from the identity table
    deployment_id = (
        op.get_bind()
        .execute(sa.select(meta.tables["identity"].c.id).limit(1))
        .scalar_one()
    )

    # Prefill the settings table with a single row that contains the deployment
    # id extracted from the former identity table and some default settings
    op.bulk_insert(
        sa.Table(
            "server_settings",
            meta,
        ),
        [
            {
                "id": deployment_id,
                # Use the deployment ID as the default server name
                "server_name": str(UUID(deployment_id)),
                # Mark existing servers as active
                "active": True,
                # Enable analytics if already enabled through the global config
                "enable_analytics": GlobalConfiguration().analytics_opt_in,
                # Enable announcements and updates by default
                "display_announcements": True,
                "display_updates": True,
                # Set the updated timestamp to the current time
                "updated": datetime.utcnow(),
            },
        ],
    )

    op.drop_table("identity")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.create_table(
        "identity",
        sa.Column("id", sa.CHAR(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Get metadata from current connection
    meta = sa.MetaData()

    # Pass in tuple with tables we want to reflect, otherwise whole database
    # will get reflected
    meta.reflect(only=("identity", "server_settings"), bind=op.get_bind())

    # Fetch the deployment id from the settings table
    deployment_id = (
        op.get_bind()
        .execute(sa.select(meta.tables["server_settings"].c.id).limit(1))
        .scalar_one()
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

    op.drop_table("server_settings")
