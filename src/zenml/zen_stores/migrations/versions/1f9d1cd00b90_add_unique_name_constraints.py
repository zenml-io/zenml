"""add unique name constraints [1f9d1cd00b90].

Revision ID: 1f9d1cd00b90
Revises: f76a368a25a5
Create Date: 2025-02-22 20:18:34.258987

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

from zenml.logger import get_logger

logger = get_logger(__name__)

# revision identifiers, used by Alembic.
revision = "1f9d1cd00b90"
down_revision = "f76a368a25a5"
branch_labels = None
depends_on = None


def resolve_duplicate_names(
    table_name: str, other_columns: list[str], session: Session
) -> None:
    """Resolve duplicate entities.

    Args:
        table_name: The name of the table to resolve duplicate entities for.
        other_columns: The columns that are part of the unique constraint,
            excluding the name column.
        session: The SQLAlchemy session to use.
    """
    columns = ["name"] + other_columns
    duplicates = session.execute(
        sa.text(
            f"""
                SELECT id, name
                FROM `{table_name}`
                WHERE ({", ".join(columns)}) IN (
                    SELECT {", ".join(columns)}
                    FROM `{table_name}`
                    GROUP BY {", ".join(columns)}
                    HAVING COUNT(*) > 1
                )
            """  # nosec B608
        )
    )
    for id_, name in list(duplicates)[1:]:
        logger.warning(f"Duplicate {table_name}: {name} (id: {id_})")
        session.execute(
            sa.text(
                f"""
                    UPDATE {table_name}
                    SET name = :new_name
                    WHERE id = :id_
                """  # nosec B608
            ),
            params={"id_": id_, "new_name": f"{name}_{id_[:6]}"},
        )


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    bind = op.get_bind()
    session = Session(bind=bind)

    resolve_duplicate_names("action", ["workspace_id"], session)

    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_action_name_in_workspace", ["name", "workspace_id"]
        )

    resolve_duplicate_names("api_key", ["service_account_id"], session)

    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_api_key_name_in_service_account",
            ["name", "service_account_id"],
        )

    resolve_duplicate_names("artifact", ["workspace_id"], session)

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.drop_constraint("unique_artifact_name", type_="unique")
        batch_op.create_unique_constraint(
            "unique_artifact_name_in_workspace", ["name", "workspace_id"]
        )

    resolve_duplicate_names("code_repository", ["workspace_id"], session)

    with op.batch_alter_table("code_repository", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_code_repository_name_in_workspace",
            ["name", "workspace_id"],
        )

    resolve_duplicate_names("event_source", ["workspace_id"], session)

    with op.batch_alter_table("event_source", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_event_source_name_in_workspace", ["name", "workspace_id"]
        )

    resolve_duplicate_names("flavor", ["type"], session)

    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_flavor_name_and_type", ["name", "type"]
        )

    resolve_duplicate_names("schedule", ["workspace_id"], session)

    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_schedule_name_in_workspace", ["name", "workspace_id"]
        )

    resolve_duplicate_names("secret", ["private", "user_id"], session)

    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_secret_name_private_scope_user",
            ["name", "private", "user_id"],
        )

    resolve_duplicate_names("service_connector", [], session)

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_service_connector_name", ["name"]
        )

    resolve_duplicate_names("stack", [], session)

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_stack_name", ["name"])

    resolve_duplicate_names("stack_component", ["type"], session)

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_component_name_and_type", ["name", "type"]
        )

    resolve_duplicate_names("tag", [], session)

    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_tag_name", ["name"])

    resolve_duplicate_names("trigger", ["workspace_id"], session)

    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_trigger_name_in_workspace", ["name", "workspace_id"]
        )

    resolve_duplicate_names("workspace", [], session)

    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_workspace_name", ["name"])


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.drop_constraint("unique_workspace_name", type_="unique")

    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_trigger_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_tag_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_component_name_and_type", type_="unique"
        )

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.drop_constraint("unique_stack_name", type_="unique")

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_service_connector_name", type_="unique"
        )

    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_secret_name_and_private_scope", type_="unique"
        )

    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_schedule_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.drop_constraint("unique_flavor_name_and_type", type_="unique")

    with op.batch_alter_table("event_source", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_event_source_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("code_repository", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_code_repository_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_artifact_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint("unique_artifact_name", ["name"])

    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_api_key_name_in_service_account", type_="unique"
        )

    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_action_name_in_workspace", type_="unique"
        )
