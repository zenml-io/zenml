"""Remove shared columns [7500f434b71c].

Revision ID: 7500f434b71c
Revises: 14d687c8fa1c
Create Date: 2023-10-16 15:15:34.865337

"""

import base64
from collections import defaultdict
from typing import Dict, Optional, Set
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from zenml.utils.time_utils import utc_now

# revision identifiers, used by Alembic.
revision = "7500f434b71c"
down_revision = "14d687c8fa1c"
branch_labels = None
depends_on = None


def _rename_duplicate_entities(
    table: sa.Table, reserved_names: Optional[Set[str]] = None
) -> None:
    """Include owner id in the name of duplicate entities.

    Args:
        table: The table in which to rename the duplicate entities.
        reserved_names: Optional reserved names not to use.
    """
    connection = op.get_bind()

    query = sa.select(
        table.c.id,
        table.c.name,
        table.c.user_id,
    )

    names = reserved_names or set()
    for id, name, user_id in connection.execute(query).fetchall():
        if user_id is None:
            # Generate a random user id
            user_id = uuid4().hex

        if name in names:
            for suffix_length in range(4, len(user_id)):
                new_name = f"{name}-{user_id[:suffix_length]}"
                if new_name not in names:
                    name = new_name
                    break

            connection.execute(
                sa.update(table).where(table.c.id == id).values(name=name)
            )

        names.add(name)


def _rename_duplicate_components(table: sa.Table) -> None:
    """Include owner id in the name of duplicate entities.

    Args:
        table: The table in which to rename the duplicate entities.
    """
    connection = op.get_bind()

    query = sa.select(
        table.c.id,
        table.c.type,
        table.c.name,
        table.c.user_id,
    )

    names_per_type: Dict[str, Set[str]] = defaultdict(lambda: {"default"})

    for id, type_, name, user_id in connection.execute(query).fetchall():
        if user_id is None:
            # Generate a random user id
            user_id = uuid4().hex

        names = names_per_type[type_]
        if name in names:
            for suffix_length in range(4, len(user_id)):
                new_name = f"{name}-{user_id[:suffix_length]}"
                if new_name not in names:
                    name = new_name
                    break

            connection.execute(
                sa.update(table).where(table.c.id == id).values(name=name)
            )

        names.add(name)


def resolve_duplicate_names() -> None:
    """Resolve duplicate names for shareable entities."""
    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(
        bind=op.get_bind(),
        only=(
            "stack",
            "stack_component",
            "stack_composition",
            "service_connector",
            "workspace",
        ),
    )

    stack_table = sa.Table("stack", meta)
    stack_component_table = sa.Table("stack_component", meta)
    stack_composition_table = sa.Table("stack_composition", meta)
    workspace_table = sa.Table("workspace", meta)
    service_connector_table = sa.Table("service_connector", meta)

    _rename_duplicate_entities(stack_table, reserved_names={"default"})
    _rename_duplicate_components(stack_component_table)
    _rename_duplicate_entities(service_connector_table)

    workspace_query = sa.select(workspace_table.c.id)
    utcnow = utc_now()

    stack_components = []
    stacks = []
    stack_compositions = []
    for row in connection.execute(workspace_query).fetchall():
        workspace_id = row[0]
        artifact_store_id = str(uuid4()).replace("-", "")
        default_artifact_store = {
            "id": artifact_store_id,
            "workspace_id": workspace_id,
            "name": "default",
            "type": "artifact_store",
            "flavor": "local",
            "configuration": base64.b64encode("{}".encode("utf-8")),
            "is_shared": True,
            "created": utcnow,
            "updated": utcnow,
        }
        orchestrator_id = str(uuid4()).replace("-", "")
        default_orchestrator = {
            "id": orchestrator_id,
            "workspace_id": workspace_id,
            "name": "default",
            "type": "orchestrator",
            "flavor": "local",
            "configuration": base64.b64encode("{}".encode("utf-8")),
            "is_shared": True,
            "created": utcnow,
            "updated": utcnow,
        }

        stack_id = str(uuid4()).replace("-", "")
        default_stack = {
            "id": stack_id,
            "workspace_id": workspace_id,
            "name": "default",
            "is_shared": True,
            "created": utcnow,
            "updated": utcnow,
        }
        stack_compositions.append(
            {"stack_id": stack_id, "component_id": artifact_store_id}
        )
        stack_compositions.append(
            {"stack_id": stack_id, "component_id": orchestrator_id}
        )
        stack_components.append(default_artifact_store)
        stack_components.append(default_orchestrator)
        stacks.append(default_stack)

    op.bulk_insert(stack_component_table, rows=stack_components)
    op.bulk_insert(stack_table, rows=stacks)
    op.bulk_insert(stack_composition_table, rows=stack_compositions)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    resolve_duplicate_names()

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.drop_column("is_shared")

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.drop_column("is_shared")

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.drop_column("is_shared")

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_shared", sa.BOOLEAN(), nullable=False)
        )

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_shared", sa.BOOLEAN(), nullable=False)
        )

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_shared", sa.BOOLEAN(), nullable=False)
        )
    # ### end Alembic commands ###
