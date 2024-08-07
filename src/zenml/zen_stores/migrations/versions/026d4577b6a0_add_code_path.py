"""Add code path [026d4577b6a0].

Revision ID: 026d4577b6a0
Revises: 909550c7c4da
Create Date: 2024-07-30 16:53:32.777594

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "026d4577b6a0"
down_revision = "909550c7c4da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("pipeline_deployment", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "code_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("pipeline_deployment", schema=None) as batch_op:
        batch_op.drop_column("code_path")

    # ### end Alembic commands ###
