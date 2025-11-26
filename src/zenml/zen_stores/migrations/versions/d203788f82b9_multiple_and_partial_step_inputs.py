"""Multiple and partial step inputs [d203788f82b9].

Revision ID: d203788f82b9
Revises: bc6317491676
Create Date: 2025-11-11 11:57:39.370022

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d203788f82b9"
down_revision = "bc6317491676"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision.

    Raises:
        NotImplementedError: If the database engine is not supported.
    """
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("item_count", sa.Integer(), nullable=True)
        )

    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column("input_index", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("chunk_index", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("chunk_size", sa.Integer(), nullable=True)
        )

    op.execute(sa.text("UPDATE step_run_input_artifact SET input_index=0"))
    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "input_index",
            nullable=False,
            existing_type=sa.Integer(),
        )

    _disable_primary_key_requirement_if_necessary()

    meta = sa.MetaData()
    meta.reflect(bind=op.get_bind(), only=["step_run_input_artifact"])
    step_run_input_artifact_table = sa.Table("step_run_input_artifact", meta)

    pk_name = step_run_input_artifact_table.primary_key.name

    if not isinstance(pk_name, str):
        engine_name = op.get_bind().engine.name
        if engine_name == "sqlite":
            pk_name = "pk_step_run_input_artifact"
        elif engine_name in {"mysql", "mariadb"}:
            pk_name = "PRIMARY"
        else:
            raise NotImplementedError(f"Unsupported engine: {engine_name}")

    with op.batch_alter_table(
        "step_run_input_artifact",
        schema=None,
        naming_convention={"pk": "pk_%(table_name)s"},
    ) as batch_op:
        # Need to first drop the foreign keys as otherwise the table renaming
        # used during the PK constraint drop/create doesn't work
        batch_op.drop_constraint(
            constraint_name="fk_step_run_input_artifact_step_id_step_run",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            constraint_name="fk_step_run_input_artifact_artifact_id_artifact_version",
            type_="foreignkey",
        )

        # Update the PK
        batch_op.drop_constraint(constraint_name=pk_name, type_="primary")
        batch_op.create_primary_key(
            constraint_name="pk_step_run_input_artifact",
            columns=["step_id", "artifact_id", "name", "input_index"],
        )

        # Re-add the foreign keys
        batch_op.create_foreign_key(
            constraint_name="fk_step_run_input_artifact_step_id_step_run",
            referent_table="step_run",
            local_cols=["step_id"],
            remote_cols=["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            constraint_name="fk_step_run_input_artifact_artifact_id_artifact_version",
            referent_table="artifact_version",
            local_cols=["artifact_id"],
            remote_cols=["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade not possible.
    """
    raise NotImplementedError("Downgrade not possible")


def _disable_primary_key_requirement_if_necessary() -> None:
    """Adjusts settings based on database engine requirements.

    Raises:
        NotImplementedError: If the database engine is not supported.
    """
    conn = op.get_bind()
    engine = conn.engine
    engine_name = engine.name.lower()

    if engine_name == "mysql":
        server_version_info = engine.dialect.server_version_info
        if server_version_info is not None and server_version_info >= (
            8,
            0,
            13,
        ):
            potential_session_var = conn.execute(
                sa.text(
                    'SHOW SESSION VARIABLES LIKE "sql_require_primary_key";'
                )
            ).fetchone()
            if potential_session_var and potential_session_var[1] == "ON":
                # Temporarily disable this MySQL setting
                # for primary key modification
                op.execute("SET SESSION sql_require_primary_key = 0;")
    elif engine_name == "mariadb":
        # mariadb doesn't support session-based scoping for this setting
        op.execute("SET GLOBAL innodb_force_primary_key = 0;")
    elif engine_name == "sqlite":
        pass
    else:
        raise NotImplementedError(f"Unsupported engine: {engine_name}")
