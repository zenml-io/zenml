"""Add model version producer run index [cd7b17d5a3c3].

Revision ID: cd7b17d5a3c3
Revises: 26351d482b9e
Create Date: 2024-12-09 14:24:21.647321

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "cd7b17d5a3c3"
down_revision = "26351d482b9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("model_version", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_numeric",
                sa.Boolean(),
                sa.Computed(
                    "name = CAST(number AS CHAR(50))",
                ),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "producer_run_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "producer_run_id_if_numeric",
                sa.CHAR(32),
                sa.Computed(
                    "CASE WHEN producer_run_id IS NOT NULL AND is_numeric = TRUE THEN producer_run_id ELSE id END",
                ),
                nullable=False,
            )
        )
        batch_op.create_index(
            "unique_numeric_version_for_pipeline_run",
            ["model_id", "producer_run_id_if_numeric"],
            unique=True,
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("model_version", schema=None) as batch_op:
        batch_op.drop_index("unique_numeric_version_for_pipeline_run")
        batch_op.drop_column("producer_run_id_with_fallback")
        batch_op.drop_column("producer_run_id")
        batch_op.drop_column("is_numeric")

    # ### end Alembic commands ###