"""Port flavors into database. [bea8a6ce3015].

Revision ID: bea8a6ce3015
Revises: 0.31.1
Create Date: 2022-12-20 11:20:30.731406

"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bea8a6ce3015"
down_revision = "0.31.1"
branch_labels = None
depends_on = None


def built_in_flavors() -> List[Dict[str, Any]]:
    """Load json file containing a json representation of all inbuilt flavors."""
    with open(
        "src/zenml/zen_stores/migrations/versions/bea8a6ce3015_port_flavors_into_database.json",
        "r",
    ) as f:
        flavors_list: List[Dict[str, Any]] = json.load(f)
        for item in flavors_list:
            item["id"] = str(uuid.uuid4()).replace("-", "")
            item["created"] = datetime.utcnow()
            item["updated"] = datetime.utcnow()

        return flavors_list


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("flavor", schema=None) as batch_op:

        batch_op.add_column(sa.Column("logo_url", sa.TEXT(), nullable=True))

        batch_op.alter_column(
            "project_id", existing_type=sa.CHAR(length=32), nullable=True
        )

        batch_op.alter_column(
            "user_id", existing_type=sa.CHAR(length=32), nullable=True
        )

    #  will get reflected
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(only=("flavor",))

    # Prefill the roles table with the admin and guest role
    op.bulk_insert(
        sa.Table(
            "flavor",
            meta,
        ),
        [*built_in_flavors()],
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("flavor", schema=None) as batch_op:

        batch_op.drop_column("logo_url")

        # TODO: all columns that don't conform to this will need to be dropped
        batch_op.alter_column(
            "project_id", existing_type=sa.CHAR(length=32), nullable=False
        )

        batch_op.alter_column(
            "user_id", existing_type=sa.CHAR(length=32), nullable=False
        )
