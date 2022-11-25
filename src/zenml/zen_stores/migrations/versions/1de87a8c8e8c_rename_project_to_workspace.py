"""Rename project to workspace [1de87a8c8e8c].

Revision ID: 1de87a8c8e8c
Revises: 0.22.0
Create Date: 2022-11-24 14:08:56.377347

"""
from collections import defaultdict
from typing import Dict, List, Tuple

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1de87a8c8e8c"
down_revision = "0.22.0"
branch_labels = None
depends_on = None


def _fk_constraint_name(source: str, target: str, source_column: str) -> str:
    """Defines the name of a foreign key constraint.

    See https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints.

    Args:
        source: Source table name.
        target: Target table name.
        source_column: Source column name.

    Returns:
        Name of the foreign key constraint.
    """
    return f"fk_{source}_{source_column}_{target}"


def _drop_fk_constraint(source: str, constraint_name: str) -> None:
    """Drops a (potentially unnamed) foreign key constraint.

    This is somewhat tricky since we have not explicitly named constraints
    before and each backend names the constraints differently. SQLite even
    doesn't name them at all.

    See https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints.

    Args:
        source: Source table name.
        constraint_name: Name of the foreign key constraint.
    """
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table(
        source, naming_convention=naming_convention
    ) as batch_op:
        batch_op.drop_constraint(
            constraint_name=constraint_name,
            type_="foreignkey",
        )


def _create_fk_constraint(
    source: str,
    target: str,
    source_column: str,
    target_column: str,
    ondelete: str,
) -> None:
    """Create a foreign key constraint.

    Args:
        source: Source table name.
        target: Target table name.
        source_column: Source column name.
        target_column: Target column name.
        ondelete: On delete behavior.
    """
    constraint_name = _fk_constraint_name(source, target, source_column)
    with op.batch_alter_table(source) as batch_op:
        batch_op.create_foreign_key(
            constraint_name=constraint_name,
            referent_table=target,
            local_cols=[source_column],
            remote_cols=[target_column],
            ondelete=ondelete,
        )


def _get_changes() -> Tuple[
    List[str],
    List[Tuple[str, str, str, str, str]],
    List[Tuple[str, str, str, str, str]],
]:
    """Define the data that should be changed in the schema.

    Returns:
        A tuple of four lists:
        - table names
        - old foreign key constraints:
            (source, target, source_column, target_column, ondelete)
        - new foreign key constraints
            (source, target, source_column, target_column, ondelete)
    """

    table_names: List[str] = [
        "flavor",
        "pipeline",
        "pipeline_run",
        "stack",
        "stack_component",
        "team_role_assignment",
        "user_role_assignment",
    ]

    new_fk_constraints: List[Tuple[str, str, str, str, str]] = [
        *[
            (source, "workspace", "workspace_id", "id", "CASCADE")
            for source in table_names
        ],
    ]
    old_fk_constraints = [
        *[
            (source, "workspace", "project_id", "id", "CASCADE")
            for source in table_names
        ],
    ]
    return table_names, new_fk_constraints, old_fk_constraints


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""

    table_names, new_fk_constraints, old_fk_constraints = _get_changes()

    engine_name = op.get_bind().engine.name

    # Under MySQL, we need to sort the old foreign keys by source table and
    # source column first since the default foreign key names contain the
    # foreign key number.
    if engine_name == "mysql":
        old_fk_constraints.sort(key=lambda x: (x[0], x[2]))
    source_table_fk_constraint_counts: Dict[str, int] = defaultdict(int)

    # Drop old foreign key constraints.
    for source, target, source_column, _, _ in old_fk_constraints:
        if engine_name == "sqlite":
            constraint_name = _fk_constraint_name(source, target, source_column)
        elif engine_name == "mysql":
            source_table_fk_constraint_counts[source] += 1
            fk_num = source_table_fk_constraint_counts[source]
            constraint_name = f"{source}_ibfk_{fk_num}"
        else:
            raise NotImplementedError(f"Unsupported engine: {engine_name}")
        _drop_fk_constraint(source, constraint_name)

    # Rename columns
    for table in table_names:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column("project_id", new_column_name="workspace_id")

    # Create new foreign key constraints
    for (
        source,
        target,
        source_column,
        target_column,
        ondelete,
    ) in new_fk_constraints:
        _create_fk_constraint(
            source, target, source_column, target_column, ondelete
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""

    table_names, new_fk_constraints, old_fk_constraints = _get_changes()

    engine_name = op.get_bind().engine.name

    # Under MySQL, we need to sort the old foreign keys by source table and
    # source column first since the default foreign key names contain the
    # foreign key number.
    if engine_name == "mysql":
        new_fk_constraints.sort(key=lambda x: (x[0], x[2]))
    source_table_fk_constraint_counts: Dict[str, int] = defaultdict(int)

    # Drop old foreign key constraints.
    for source, target, source_column, _, _ in new_fk_constraints:
        if engine_name == "sqlite":
            constraint_name = _fk_constraint_name(source, target, source_column)
        elif engine_name == "mysql":
            source_table_fk_constraint_counts[source] += 1
            fk_num = source_table_fk_constraint_counts[source]
            constraint_name = f"{source}_ibfk_{fk_num}"
        else:
            raise NotImplementedError(f"Unsupported engine: {engine_name}")
        _drop_fk_constraint(source, constraint_name)

    # Rename columns
    for table in table_names:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column("workspace_id", new_column_name="project_id")

    # Create new foreign key constraints
    for (
        source,
        target,
        source_column,
        target_column,
        ondelete,
    ) in old_fk_constraints:
        _create_fk_constraint(
            source, target, source_column, target_column, ondelete
        )

