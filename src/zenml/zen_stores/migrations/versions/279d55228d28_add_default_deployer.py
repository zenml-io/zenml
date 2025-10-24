"""add default deployer [279d55228d28].

Revision ID: 279d55228d28
Revises: 124b57b8c7b1
Create Date: 2025-10-23 18:12:26.232710

"""

import base64
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from zenml.utils.time_utils import utc_now

# revision identifiers, used by Alembic.
revision = "279d55228d28"
down_revision = "124b57b8c7b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database data to add a default deployer component."""
    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(
        bind=connection,
        only=("stack", "stack_component", "stack_composition"),
    )

    stack_table = sa.Table("stack", meta)
    component_table = sa.Table("stack_component", meta)
    composition_table = sa.Table("stack_composition", meta)

    default_stack = connection.execute(
        sa.select(stack_table.c.id)
        .where(stack_table.c.name == "default")
        .limit(1)
    ).fetchone()

    if not default_stack:
        return

    default_stack_id = default_stack[0]
    if not default_stack_id:
        return

    now = utc_now()
    empty_config = base64.b64encode("{}".encode("utf-8"))

    # If an existing default deployer exists, rename it to avoid conflicts
    existing_default = connection.execute(
        sa.select(component_table.c.id)
        .where(component_table.c.name == "default")
        .where(component_table.c.type == "deployer")
        .limit(1)
    ).fetchone()

    if existing_default:
        existing_id = existing_default[0]
        suffix = str(existing_id)[:8]
        connection.execute(
            sa.update(component_table)
            .where(component_table.c.id == existing_id)
            .values(name=f"default_{suffix}", updated=now)
        )

    component_id = uuid4().hex
    connection.execute(
        sa.insert(component_table).values(
            id=component_id,
            name="default",
            type="deployer",
            flavor="local",
            configuration=empty_config,
            created=now,
            updated=now,
        )
    )

    connection.execute(
        sa.insert(composition_table).values(
            stack_id=default_stack_id, component_id=component_id
        )
    )


def downgrade() -> None:
    """No downgrade supported for this data migration."""
    pass
