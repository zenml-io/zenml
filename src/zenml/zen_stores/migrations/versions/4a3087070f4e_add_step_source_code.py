"""Add step source code [4a3087070f4e].

Revision ID: 4a3087070f4e
Revises: d7b3acf9aa46
Create Date: 2023-01-12 21:17:14.959401

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4a3087070f4e"
down_revision = "d7b3acf9aa46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_code", sa.TEXT(), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("source_code")

    # ### end Alembic commands ###
