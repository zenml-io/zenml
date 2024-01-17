"""Add identity table [7e4a481d17f7].

Revision ID: 7e4a481d17f7
Revises: 0.30.0
Create Date: 2022-12-08 16:27:48.909015

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "7e4a481d17f7"
down_revision = "0.30.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    from zenml.config.global_config import GlobalConfiguration

    op.create_table(
        "identity",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # get metadata from current connection
    meta = sa.MetaData(bind=op.get_bind())

    # pass in tuple with tables we want to reflect, otherwise whole database
    #  will get reflected
    meta.reflect(only=("identity",))
    # Prefill the identity table with a single row that contains the deployment
    # id extracted from the global configuration
    op.bulk_insert(
        sa.Table(
            "identity",
            meta,
        ),
        [
            {
                "id": str(GlobalConfiguration().user_id).replace("-", ""),
            },
        ],
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_table("identity")
