"""Rename tables [5330ba58bf20].

Revision ID: 5330ba58bf20
Revises: d02b3d3464cf
Create Date: 2022-11-03 16:33:15.220179

"""
from typing import Dict, List, Tuple

from alembic import op

# revision identifiers, used by Alembic.
revision = "5330ba58bf20"
down_revision = "d02b3d3464cf"
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


def _drop_fk_constraint(source: str, target: str, source_column: str) -> None:
    """Drops a (potentially unnamed) foreign key constraint.

    This is somewhat tricky since we have not explicitly named constraints
    before and each backend names the constraints differently. SQLite even
    doesn't name them at all.

    See https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints.

    Args:
        source: Source table name.
        target: Target table name.
        source_column: Source column name.
        target_column: Target column name.
    """
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    constraint_name = _fk_constraint_name(source, target, source_column)
    with op.batch_alter_table(
        source, naming_convention=naming_convention
    ) as batch_op:
        batch_op.drop_constraint(
            constraint_name=constraint_name,
            type_="foreignkey",
        )


def _create_fk_constraint(
    source: str, target: str, source_column: str, target_column: str
) -> None:
    """Create a foreign key constraint.

    Args:
        source: Source table name.
        target: Target table name.
        source_column: Source column name.
        target_column: Target column name.
    """
    constraint_name = _fk_constraint_name(source, target, source_column)
    with op.batch_alter_table(source) as batch_op:
        batch_op.create_foreign_key(
            constraint_name=constraint_name,
            referent_table=target,
            local_cols=[source_column],
            remote_cols=[target_column],
        )


def _get_changes() -> Tuple[
    List[str],
    List[str],
    List[Tuple[str, str, str, str]],
    List[Tuple[str, str, str, str]],
]:
    """Define the data that should be changed in the schema.

    Returns:
        A tuple of four lists:
        - old table names
        - new table names
        - old foreign key constraints
        - new foreign key constraints
    """
    # Define all the tables that should be renamed
    table_name_mapping: Dict[str, str] = {
        "roleschema": "role",
        "stepinputartifactschema": "step_run_artifact",
        "userroleassignmentschema": "user_role_assignment",
        "steprunorderschema": "step_run_parents",
        "teamschema": "team",
        "artifactschema": "artifacts",
        "pipelinerunschema": "pipeline_run",
        "steprunschema": "step_run",
        "teamassignmentschema": "team_assignment",
        "projectschema": "project",
        "flavorschema": "flavor",
        "userschema": "user",
        "stackcomponentschema": "stack_component",
        "pipelineschema": "pipeline",
        "stackcompositionschema": "stack_composition",
        "teamroleassignmentschema": "team_role_assignment",
        "stackschema": "stack",
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
        "user_role_assignment",
    ]
    new_fk_constraints: List[Tuple[str, str, str, str]] = [
        *[
            (source, "project", "project_id", "id")
            for source in project_user_fk_tables
        ],  # 6
        *[
            (source, "user", "user_id", "id")
            for source in project_user_fk_tables
        ],  # 12
        ("stack_composition", "stack", "stack_id", "id"),  # 13
        ("stack_composition", "stack_component", "component_id", "id"),  # 14
        ("pipeline_run", "pipeline", "pipeline_id", "id"),  # 15
        ("pipeline_run", "stack", "stack_id", "id"),  # 16
        ("step_run", "pipeline_run", "pipeline_run_id", "id"),  # 17
        ("step_run_artifact", "step_run", "step_id", "id"),  # 18
        ("step_run_artifact", "artifacts", "artifact_id", "id"),  # 19
        ("step_run_parents", "step_run", "parent_id", "id"),  # 20
        ("step_run_parents", "step_run", "child_id", "id"),  # 21
        ("artifacts", "step_run", "producer_step_id", "id"),  # 22
        ("artifacts", "step_run", "parent_step_id", "id"),  # 23
        ("team_assignment", "user", "user_id", "id"),  # 24
        ("team_assignment", "team", "team_id", "id"),  # 25
        ("team_role_assignment", "team", "team_id", "id"),  # 26
        ("team_role_assignment", "role", "role_id", "id"),  # 27
        ("team_role_assignment", "project", "project_id", "id"),  # 28
        ("user_role_assignment", "role", "role_id", "id"),  # 29
    ]
    old_fk_constraints = [
        (
            reversed_table_name_mapping[source],
            reversed_table_name_mapping[target],
            source_col,
            target_col,
        )
        for source, target, source_col, target_col in new_fk_constraints
    ]
    return (
        old_table_names,
        new_table_names,
        old_fk_constraints,
        new_fk_constraints,
    )


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""

    (
        old_table_names,
        new_table_names,
        old_fk_constraints,
        new_fk_constraints,
    ) = _get_changes()

    # Drop old foreign key constraints
    for source, target, source_column, target_column in old_fk_constraints:
        _drop_fk_constraint(source, target, source_column)

    # Rename tables
    for old_table_name, new_table_name in zip(old_table_names, new_table_names):
        op.rename_table(old_table_name, new_table_name)

    # Create new foreign key constraints
    for source, target, source_column, target_column in new_fk_constraints:
        _create_fk_constraint(source, target, source_column, target_column)


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""

    (
        old_table_names,
        new_table_names,
        old_fk_constraints,
        new_fk_constraints,
    ) = _get_changes()

    # Drop new foreign key constraints
    for source, target, source_column, target_column in new_fk_constraints:
        _drop_fk_constraint(source, target, source_column)

    # Rename tables
    for old_table_name, new_table_name in zip(old_table_names, new_table_names):
        op.rename_table(new_table_name, old_table_name)

    # Create old foreign key constraints
    for source, target, source_column, target_column in old_fk_constraints:
        _create_fk_constraint(source, target, source_column, target_column)
