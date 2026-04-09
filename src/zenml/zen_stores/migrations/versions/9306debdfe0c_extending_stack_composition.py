"""extending stack composition [9306debdfe0c].

Revision ID: 9306debdfe0c
Revises: 0.94.2
Create Date: 2026-03-31 15:41:03.431700

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9306debdfe0c"
down_revision = "0.94.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("stack_composition", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("default_for_type", sa.String(), nullable=True)
        )

    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(
        bind=connection,
        only=("stack_component", "stack_composition"),
    )

    component_table = sa.Table("stack_component", meta)
    composition_table = sa.Table("stack_composition", meta)

    compositions = connection.execute(
        sa.select(
            composition_table.c.stack_id,
            composition_table.c.component_id,
            component_table.c.type,
        )
        .select_from(
            composition_table.join(
                component_table,
                composition_table.c.component_id == component_table.c.id,
            )
        )
        .order_by(
            composition_table.c.stack_id,
            component_table.c.type,
            composition_table.c.component_id,
        )
    ).fetchall()

    seen_defaults = set()
    for composition in compositions:
        default_key = (composition.stack_id, composition.type)
        default_for_type = None
        if default_key not in seen_defaults:
            default_for_type = composition.type
            seen_defaults.add(default_key)

        connection.execute(
            sa.update(composition_table)
            .where(composition_table.c.stack_id == composition.stack_id)
            .where(
                composition_table.c.component_id == composition.component_id
            )
            .values(
                default_for_type=default_for_type,
            )
        )

    with op.batch_alter_table("stack_composition", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_default_stack_component_type",
            ["stack_id", "default_for_type"],
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("stack_composition", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_default_stack_component_type",
            type_="unique",
        )
        batch_op.drop_column("default_for_type")
