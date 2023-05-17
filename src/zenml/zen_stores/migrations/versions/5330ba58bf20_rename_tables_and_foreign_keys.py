"""Rename tables and foreign keys [5330ba58bf20].

Revision ID: 5330ba58bf20
Revises: 7280c14811d6
Create Date: 2022-11-03 16:33:15.220179

"""
from collections import defaultdict
from typing import Dict, List, Tuple

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5330ba58bf20"
down_revision = "7280c14811d6"
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


def _get_changes() -> (
    Tuple[
        List[str],
        List[str],
        List[str],
        List[Tuple[str, str, str, str, str]],
        List[Tuple[str, str, str, str, str]],
    ]
):
    """Define the data that should be changed in the schema.

    Returns:
        A tuple of four lists:
        - old table names
        - new table names
        - new table names of tables that should have a `NOT NULL` constraint
            on the `project_id` column
        - old foreign key constraints:
            (source, target, source_column, target_column, ondelete)
        - new foreign key constraints
            (source, target, source_column, target_column, ondelete)
    """
    # Define all the tables that should be renamed
    table_name_mapping: Dict[str, str] = {
        "roleschema": "role",
        "stepinputartifactschema": "step_run_input_artifact",
        "userroleassignmentschema": "user_role_assignment",
        "steprunorderschema": "step_run_parents",
        "teamschema": "team",
        "artifactschema": "artifacts",
        "pipelinerunschema": "pipeline_run",
        "steprunschema": "step_run",
        "teamassignmentschema": "team_assignment",
        "projectschema": "workspace",
        "flavorschema": "flavor",
        "userschema": "user",
        "stackcomponentschema": "stack_component",
        "pipelineschema": "pipeline",
        "stackcompositionschema": "stack_composition",
        "teamroleassignmentschema": "team_role_assignment",
        "stackschema": "stack",
        "rolepermissionschema": "role_permission",
    }
    reversed_table_name_mapping = {v: k for k, v in table_name_mapping.items()}
    old_table_names = list(table_name_mapping.keys())
    new_table_names = list(table_name_mapping.values())

    # Define all foreign key constraints that need to be adjusted
    project_user_fk_tables = [
        "stack_component",
        "flavor",
        "pipeline",
        "pipeline_run",
        "stack",
    ]
    new_fk_constraints: List[Tuple[str, str, str, str, str]] = [
        *[
            (source, "workspace", "project_id", "id", "CASCADE")
            for source in project_user_fk_tables
        ],  # 5
        *[
            (source, "user", "user_id", "id", "SET NULL")
            for source in project_user_fk_tables
        ],  # 10
        ("stack_composition", "stack", "stack_id", "id", "CASCADE"),  # 11
        (
            "stack_composition",
            "stack_component",
            "component_id",
            "id",
            "CASCADE",
        ),  # 12
        ("pipeline_run", "pipeline", "pipeline_id", "id", "SET NULL"),  # 13
        ("pipeline_run", "stack", "stack_id", "id", "SET NULL"),  # 14
        ("step_run", "pipeline_run", "pipeline_run_id", "id", "CASCADE"),  # 15
        (
            "step_run_input_artifact",
            "step_run",
            "step_id",
            "id",
            "CASCADE",
        ),  # 16
        (
            "step_run_input_artifact",
            "artifacts",
            "artifact_id",
            "id",
            "CASCADE",
        ),  # 17
        ("step_run_parents", "step_run", "parent_id", "id", "CASCADE"),  # 18
        ("step_run_parents", "step_run", "child_id", "id", "CASCADE"),  # 19
        ("artifacts", "step_run", "producer_step_id", "id", "CASCADE"),  # 20
        ("artifacts", "step_run", "parent_step_id", "id", "CASCADE"),  # 21
        ("team_assignment", "user", "user_id", "id", "CASCADE"),  # 22
        ("team_assignment", "team", "team_id", "id", "CASCADE"),  # 23
        ("team_role_assignment", "team", "team_id", "id", "CASCADE"),  # 24
        ("team_role_assignment", "role", "role_id", "id", "CASCADE"),  # 25
        (
            "team_role_assignment",
            "workspace",
            "project_id",
            "id",
            "CASCADE",
        ),  # 26
        ("user_role_assignment", "user", "user_id", "id", "CASCADE"),  # 27
        ("user_role_assignment", "role", "role_id", "id", "CASCADE"),  # 28
        (
            "user_role_assignment",
            "workspace",
            "project_id",
            "id",
            "CASCADE",
        ),  # 29
        ("role_permission", "role", "role_id", "id", "CASCADE"),  # 30
    ]
    old_fk_constraints = [
        (
            reversed_table_name_mapping[source],
            reversed_table_name_mapping[target],
            source_col,
            target_col,
            ondelete,
        )
        for source, target, source_col, target_col, ondelete in new_fk_constraints
    ]
    return (
        old_table_names,
        new_table_names,
        project_user_fk_tables,
        old_fk_constraints,
        new_fk_constraints,
    )


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision.

    Raises:
        NotImplementedError: If the database engine is not SQLite or MySQL.
    """
    (
        old_table_names,
        new_table_names,
        project_not_null_tables,
        old_fk_constraints,
        new_fk_constraints,
    ) = _get_changes()

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
            constraint_name = _fk_constraint_name(
                source, target, source_column
            )
        elif engine_name == "mysql":
            source_table_fk_constraint_counts[source] += 1
            fk_num = source_table_fk_constraint_counts[source]
            constraint_name = f"{source}_ibfk_{fk_num}"
        else:
            raise NotImplementedError(f"Unsupported engine: {engine_name}")
        _drop_fk_constraint(source, constraint_name)

    # Rename tables
    for old_table_name, new_table_name in zip(
        old_table_names, new_table_names
    ):
        op.rename_table(old_table_name, new_table_name)

    # Set `project_id` to `NOT NULL` where appropriate.
    for table_name in project_not_null_tables:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.alter_column(
                "project_id", existing_type=sa.CHAR(length=32), nullable=False
            )

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
    (
        old_table_names,
        new_table_names,
        project_not_null_tables,
        old_fk_constraints,
        new_fk_constraints,
    ) = _get_changes()

    # Drop new foreign key constraints
    for source, target, source_column, _, _ in new_fk_constraints:
        constraint_name = _fk_constraint_name(source, target, source_column)
        _drop_fk_constraint(source, constraint_name)

    # Remove `project_id NOT NULL` where appropriate.
    for table_name in project_not_null_tables:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.alter_column(
                "project_id", existing_type=sa.CHAR(length=32), nullable=True
            )

    # Rename tables
    for old_table_name, new_table_name in zip(
        old_table_names, new_table_names
    ):
        op.rename_table(new_table_name, old_table_name)

    # Create old foreign key constraints
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
