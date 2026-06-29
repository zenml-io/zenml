"""detach deployer from stack [d7ebd154242a].

Revision ID: d7ebd154242a
Revises: c1d964b6075c
Create Date: 2026-06-29 10:25:33.000930

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d7ebd154242a"
down_revision = "c1d964b6075c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("deployment", schema=None) as batch_op:
        batch_op.add_column(sa.Column("build_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_deployment_build_id_pipeline_build",
            "pipeline_build",
            ["build_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Detach every deployer from every stack while keeping the deployer
    # components themselves. Deployers are selected explicitly at deploy time
    # and are no longer part of the stack aggregation.
    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(
        bind=connection,
        only=("stack_component", "stack_composition"),
    )

    component_table = sa.Table("stack_component", meta)
    composition_table = sa.Table("stack_composition", meta)

    deployer_ids = connection.execute(
        sa.select(component_table.c.id).where(
            component_table.c.type == "deployer"
        )
    ).fetchall()

    if deployer_ids:
        connection.execute(
            sa.delete(composition_table).where(
                composition_table.c.component_id.in_(
                    [row[0] for row in deployer_ids]
                )
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("deployment", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_deployment_build_id_pipeline_build", type_="foreignkey"
        )
        batch_op.drop_column("build_id")
