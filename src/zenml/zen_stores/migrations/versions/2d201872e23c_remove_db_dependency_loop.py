"""remove db dependency loop [2d201872e23c].

Revision ID: 2d201872e23c
Revises: 0.56.3
Create Date: 2024-04-11 09:47:47.557220

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2d201872e23c"
down_revision = "0.56.3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline_build", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_pipeline_build_template_deployment_id_pipeline_deployment",
            type_="foreignkey",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
