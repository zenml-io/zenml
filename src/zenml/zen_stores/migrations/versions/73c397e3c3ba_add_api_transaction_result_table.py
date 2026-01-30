"""add api transaction result table [73c397e3c3ba].

Revision ID: 73c397e3c3ba
Revises: d1e8c2c4a9ef
Create Date: 2026-01-23 18:51:29.944099

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMBLOB

# revision identifiers, used by Alembic.
revision = "73c397e3c3ba"
down_revision = "d1e8c2c4a9ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        "api_transaction_result",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column(
            "result",
            MEDIUMBLOB
            if op.get_bind().dialect.name == "mysql"
            else sa.LargeBinary(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["api_transaction.id"],
            name="fk_api_transaction_result_id_api_transaction",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("api_transaction", schema=None) as batch_op:
        batch_op.drop_column("result")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("api_transaction", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("result", sa.VARCHAR(length=16777215), nullable=True)
        )

    op.drop_table("api_transaction_result")
